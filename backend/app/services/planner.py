"""Hybrid Weekly Meal Planner: Deterministic multi-objective scoring + Local LLM Structured Planning.

Optimizes for:
- Adjustable people count (servings_per_meal) & days (1..7)
- Cooking effort level (1=Ultra-Simpel, 2=Alltag, 3=Ambitioniert)
- High protein & complex carbohydrates (fiber + complex_carb_ratio)
- Weekly budget & ALDI/weekly promo deals
- Pantry expiry-first leftover utilization
- Smart batch-cooking (cook once, eat twice without double-counting groceries)
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from sqlalchemy.orm import Session

from ..models import (
    AppSettings,
    Ingredient,
    IngredientOfferMatch,
    MealPlan,
    MealPlanEntry,
    PantryItem,
    PriceOffer,
    Recipe,
    RecipeIngredient,
)
from ..schemas import (
    LlmGeneratedRecipeSchema,
    LlmWeeklyPlanDraftSchema,
    MealPlanGenerateRequest,
)
from .llm_client import LocalLlmClient
from .nutrition import amount_in_default_unit, recalculate_recipe_metrics
from .shopping import rebuild_shopping_list


DIET_COMPATIBILITY = {
    "omnivore": {"omnivore", "pescatarian", "vegetarian", "vegan"},
    "pescatarian": {"pescatarian", "vegetarian", "vegan"},
    "vegetarian": {"vegetarian", "vegan"},
    "vegan": {"vegan"},
}


EQUIPMENT_LABELS = {
    "airfryer": "Airfryer (Heißluftfritteuse)",
    "stove_2_burners": "Herd mit 2 Platten",
    "stove_4_burners": "Herd mit 4 Platten",
    "oven": "Backofen",
    "microwave": "Mikrowelle",
    "blender": "Mixer / Pürierstab",
    "rice_cooker": "Reiskocher",
}


def _get_equipment(app_settings: AppSettings) -> set[str]:
    try:
        return set(
            json.loads(
                app_settings.kitchen_equipment_json
                or '["airfryer", "stove_2_burners", "oven"]'
            )
        )
    except Exception:
        return {"airfryer", "stove_2_burners", "oven"}


def _equipment_prompt_rules(app_settings: AppSettings) -> str:
    eq = _get_equipment(app_settings)
    have = [EQUIPMENT_LABELS.get(k, k) for k in eq]
    rules = [f"Verfügbare Küchengeräte: {', '.join(have) or 'Herd'}."]
    if "microwave" not in eq:
        rules.append("WICHTIG: KEINE Mikrowelle vorhanden — niemals Mikrowelle für Zubereitung oder Aufwärmen vorschlagen!")
    if "stove_2_burners" in eq and "stove_4_burners" not in eq:
        rules.append("Es gibt nur 2 Herdplatten — maximal 2 Töpfe/Pfannen gleichzeitig nutzen.")
    if "airfryer" in eq:
        rules.append("Nutze gerne den Airfryer für schnelle, knusprige und abwascharme Gerichte.")
    if "blender" not in eq:
        rules.append("Kein Standmixer vorausgesetzt — nur einfache Hand-Zubereitung ohne zwingendes Mixen.")
    return " ".join(rules)


def next_monday_iso() -> str:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def _get_pantry_priority_ingredients(db: Session) -> dict[int, float]:
    """Return ingredient_id -> urgency bonus score based on pantry quantity & expiry date."""
    bonuses: dict[int, float] = {}
    today = date.today()
    for item in db.query(PantryItem).filter(PantryItem.quantity > 0).all():
        score = 8.0
        if item.use_priority == "urgent":
            score = 30.0
        elif item.use_priority == "use_soon":
            score = 20.0
        if item.expires_at:
            try:
                exp = date.fromisoformat(item.expires_at[:10])
                days_left = (exp - today).days
                if days_left <= 2:
                    score = max(score, 35.0)
                elif days_left <= 5:
                    score = max(score, 22.0)
            except ValueError:
                pass
        bonuses[item.ingredient_id] = max(bonuses.get(item.ingredient_id, 0.0), score)
    return bonuses


def _get_promo_ingredient_ids(db: Session) -> set[int]:
    today_str = date.today().isoformat()
    rows = (
        db.query(IngredientOfferMatch.ingredient_id, PriceOffer.valid_to)
        .join(PriceOffer, IngredientOfferMatch.offer_id == PriceOffer.id)
        .filter(
            IngredientOfferMatch.is_rejected.is_(False),
            IngredientOfferMatch.confidence >= 0.60,
        )
        .all()
    )
    return {ing_id for ing_id, valid_to in rows if not valid_to or valid_to >= today_str}


def _recipe_fits_constraints(
    recipe: Recipe,
    slot: str,
    max_effort: int,
    allowed_diets: set[str],
    excluded_terms: list[str],
) -> bool:
    meal_types = json.loads(recipe.meal_types_json or "[]")
    if slot not in meal_types:
        return False
    if recipe.effort_level > max_effort:
        return False
    if recipe.diet_type not in allowed_diets:
        return False
    if excluded_terms:
        title_l = recipe.title.lower()
        ing_names = " ".join(
            (ri.ingredient.name.lower() if ri.ingredient else "")
            for ri in recipe.ingredients
        )
        for term in excluded_terms:
            t = term.strip().lower()
            if t and (t in title_l or t in ing_names):
                return False
    return True


def _score_recipe_for_slot(
    recipe: Recipe,
    slot: str,
    app_settings: AppSettings,
    pantry_bonuses: dict[int, float],
    promo_ids: set[int],
    used_counts: dict[int, int],
    planned_ingredient_ids: set[int],
    target_slot_kcal: float,
    target_slot_protein: float,
    budget_per_serving: float,
    prefer_pantry: bool,
    prefer_offers: bool,
) -> float:
    score = 50.0

    # Protein density reward
    protein_diff = abs(recipe.protein_g - target_slot_protein)
    score += max(0.0, 22.0 - protein_diff * 0.5)
    if recipe.protein_g >= target_slot_protein * 0.85:
        score += 8.0

    # Calorie fit reward
    kcal_diff = abs(recipe.kcal_per_serving - target_slot_kcal)
    score += max(0.0, 18.0 - kcal_diff * 0.04)

    # Complex carbs & fiber bonus (core user preference!)
    if app_settings.prefer_complex_carbs:
        score += (recipe.complex_carb_ratio / 100.0) * 14.0
        score += min(recipe.fiber_g, 16.0) * 0.8

    # Budget awareness
    if recipe.estimated_cost_per_serving <= budget_per_serving:
        score += 10.0
    else:
        score -= (recipe.estimated_cost_per_serving - budget_per_serving) * 7.0

    # Ingredient synergy bonus: reuse ingredients already planned this week to minimize waste & checkout cost
    if planned_ingredient_ids:
        shared = sum(
            1
            for ri in recipe.ingredients
            if ri.ingredient_id in planned_ingredient_ids
            and ri.ingredient
            and not ri.ingredient.is_pantry_staple
        )
        score += min(shared * 4.5, 22.0)

    # Pantry leftover boost
    if prefer_pantry:
        pantry_hits = sum(
            pantry_bonuses.get(ri.ingredient_id, 0.0) for ri in recipe.ingredients
        )
        score += min(pantry_hits, 40.0)

    # Weekly supermarket offer boost
    if prefer_offers and promo_ids:
        offer_hits = sum(1 for ri in recipe.ingredients if ri.ingredient_id in promo_ids)
        score += min(offer_hits * 9.0, 27.0)

    # Kitchen equipment affinity (e.g. Airfryer boost, respect missing blender)
    equipment = _get_equipment(app_settings)
    recipe_tags = set(json.loads(recipe.tags_json or "[]"))
    if "airfryer" in equipment and "airfryer" in recipe_tags:
        score += 10.0
    elif "airfryer" not in equipment and "airfryer" in recipe_tags:
        score -= 40.0

    # Favorite boost
    if recipe.is_favorite:
        score += 10.0

    # Variety penalty: keep lunches/dinners fresh, allow practical 2-3x repeat on breakfast/snack
    repeats = used_counts.get(recipe.id, 0)
    if repeats > 0:
        if slot in ("breakfast", "snack"):
            score -= 8.0 if repeats == 1 else (22.0 if repeats == 2 else repeats * 30.0)
        else:
            score -= repeats * 36.0

    # Small controlled jitter for fresh plans on regeneration
    score += random.uniform(-4.0, 4.0)
    return score


def _slot_macro_shares(active_slots: list[str]) -> dict[str, float]:
    raw_weights = {
        "breakfast": 0.24,
        "lunch": 0.34,
        "dinner": 0.30,
        "snack": 0.12,
    }
    total = sum(raw_weights.get(s, 0.25) for s in active_slots) or 1.0
    return {s: raw_weights.get(s, 0.25) / total for s in active_slots}


def generate_meal_plan(db: Session, req: MealPlanGenerateRequest) -> MealPlan:
    """Generate a full weekly meal plan via deterministic optimization or local LLM."""
    app_settings = db.get(AppSettings, 1)
    if not app_settings:
        raise RuntimeError("AppSettings not initialized")

    diet_type = req.diet_type or app_settings.diet_type or "omnivore"
    allowed_diets = DIET_COMPATIBILITY.get(diet_type, DIET_COMPATIBILITY["omnivore"])
    excluded_terms = json.loads(app_settings.excluded_ingredients_json or "[]")
    target_budget = req.target_budget_eur or app_settings.weekly_budget_eur
    week_start = req.week_start_date or next_monday_iso()
    active_slots = req.active_slots or ["breakfast", "lunch", "dinner", "snack"]

    # Archive previous active plan
    db.query(MealPlan).filter(MealPlan.status == "active").update({"status": "archived"})

    all_recipes = db.query(Recipe).all()
    pantry_bonuses = _get_pantry_priority_ingredients(db)
    promo_ids = _get_promo_ingredient_ids(db)
    slot_shares = _slot_macro_shares(active_slots)

    # Budget per serving rough target
    total_servings_week = max(req.days_count * req.servings_per_meal * len(active_slots), 1)
    budget_per_serving = target_budget / total_servings_week

    rationale = (
        f"Optimiert für {req.servings_per_meal} {'Person' if req.servings_per_meal == 1 else 'Personen'}, "
        f"max. Aufwand Stufe {req.max_effort_level}, Fokus auf Protein (~{app_settings.protein_g_target}g/Tag) "
        f"& komplexe Kohlenhydrate bei ~{target_budget:.0f} € Wochenbudget."
    )

    llm_choices: list[tuple[int, str, int, int | None, str | None]] | None = None
    if req.use_ai:
        llm_choices, ai_rationale = _try_llm_weekly_plan(
            db=db,
            app_settings=app_settings,
            req=req,
            all_recipes=all_recipes,
            allowed_diets=allowed_diets,
            excluded_terms=excluded_terms,
            pantry_bonuses=pantry_bonuses,
            promo_ids=promo_ids,
        )
        if llm_choices:
            rationale = ai_rationale

    plan = MealPlan(
        title=f"Wochenplan ab {week_start}",
        week_start_date=week_start,
        days_count=req.days_count,
        servings_per_meal=req.servings_per_meal,
        max_effort_level=req.max_effort_level,
        target_budget_eur=target_budget,
        active_slots_json=json.dumps(active_slots),
        batch_cooking=req.batch_cooking,
        status="active",
        llm_rationale=rationale,
    )
    db.add(plan)
    db.flush()

    if llm_choices:
        # Insert AI-selected slots and wire batch-cooking leftover links
        created_by_day_slot: dict[tuple[int, str], MealPlanEntry] = {}
        valid_recipe_ids = {r.id for r in all_recipes}
        for day_idx, slot, recipe_id, leftover_of_day, note in llm_choices:
            if day_idx >= req.days_count or slot not in active_slots:
                continue
            if recipe_id not in valid_recipe_ids:
                continue
            parent_id = None
            if leftover_of_day is not None:
                parent_entry = created_by_day_slot.get((leftover_of_day, slot)) or created_by_day_slot.get((leftover_of_day, "dinner"))
                if parent_entry and parent_entry.recipe_id == recipe_id:
                    parent_id = parent_entry.id
            entry = MealPlanEntry(
                meal_plan_id=plan.id,
                day_of_week=day_idx,
                slot=slot,
                recipe_id=recipe_id,
                servings=req.servings_per_meal,
                is_leftover_from_entry_id=parent_id,
                notes=note,
            )
            db.add(entry)
            db.flush()
            created_by_day_slot[(day_idx, slot)] = entry
    else:
        _populate_deterministic_plan(
            db=db,
            plan=plan,
            req=req,
            app_settings=app_settings,
            all_recipes=all_recipes,
            allowed_diets=allowed_diets,
            excluded_terms=excluded_terms,
            pantry_bonuses=pantry_bonuses,
            promo_ids=promo_ids,
            slot_shares=slot_shares,
            budget_per_serving=budget_per_serving,
        )

    db.commit()
    db.refresh(plan)
    rebuild_shopping_list(db, plan)
    db.refresh(plan)
    return plan


def _populate_deterministic_plan(
    db: Session,
    plan: MealPlan,
    req: MealPlanGenerateRequest,
    app_settings: AppSettings,
    all_recipes: list[Recipe],
    allowed_diets: set[str],
    excluded_terms: list[str],
    pantry_bonuses: dict[int, float],
    promo_ids: set[int],
    slot_shares: dict[str, float],
    budget_per_serving: float,
) -> None:
    used_counts: dict[int, int] = {}
    planned_ingredient_ids: set[int] = set()
    entries_by_day_slot: dict[tuple[int, str], MealPlanEntry] = {}

    for day in range(req.days_count):
        for slot in req.active_slots:
            # Smart Batch-Cooking: If dinner yesterday was a meal-prep recipe, reuse as today's lunch!
            if (
                req.batch_cooking
                and slot == "lunch"
                and day > 0
                and day % 2 == 1
                and (day - 1, "dinner") in entries_by_day_slot
            ):
                prev_dinner = entries_by_day_slot[(day - 1, "dinner")]
                prev_tags = json.loads(prev_dinner.recipe.tags_json or "[]")
                if "meal-prep" in prev_tags or "one-pot" in prev_tags or "airfryer" in prev_tags:
                    eq = _get_equipment(app_settings)
                    reheat_hint = (
                        "kurz in Pfanne/Airfryer erwärmen"
                        if "microwave" not in eq
                        else "kurz aufwärmen"
                    )
                    entry = MealPlanEntry(
                        meal_plan_id=plan.id,
                        day_of_week=day,
                        slot=slot,
                        recipe_id=prev_dinner.recipe_id,
                        servings=req.servings_per_meal,
                        is_leftover_from_entry_id=prev_dinner.id,
                        notes=f"Batch-Cooking Rest vom Vortag (doppelt kochen, {reheat_hint})",
                    )
                    db.add(entry)
                    db.flush()
                    entries_by_day_slot[(day, slot)] = entry
                    continue

            candidates = [
                r
                for r in all_recipes
                if _recipe_fits_constraints(
                    r, slot, req.max_effort_level, allowed_diets, excluded_terms
                )
            ]
            # Relax effort filter gracefully if very strict diet left no options
            if not candidates:
                candidates = [
                    r
                    for r in all_recipes
                    if _recipe_fits_constraints(r, slot, 3, allowed_diets, excluded_terms)
                ]
            if not candidates:
                candidates = all_recipes

            share = slot_shares.get(slot, 0.25)
            scored = sorted(
                candidates,
                key=lambda r: _score_recipe_for_slot(
                    recipe=r,
                    slot=slot,
                    app_settings=app_settings,
                    pantry_bonuses=pantry_bonuses,
                    promo_ids=promo_ids,
                    used_counts=used_counts,
                    planned_ingredient_ids=planned_ingredient_ids,
                    target_slot_kcal=app_settings.kcal_target * share,
                    target_slot_protein=app_settings.protein_g_target * share,
                    budget_per_serving=budget_per_serving,
                    prefer_pantry=req.prefer_pantry_leftovers,
                    prefer_offers=req.prefer_offers,
                ),
                reverse=True,
            )

            chosen = scored[0]
            used_counts[chosen.id] = used_counts.get(chosen.id, 0) + 1
            for ri in chosen.ingredients:
                planned_ingredient_ids.add(ri.ingredient_id)

            entry = MealPlanEntry(
                meal_plan_id=plan.id,
                day_of_week=day,
                slot=slot,
                recipe_id=chosen.id,
                servings=req.servings_per_meal,
            )
            entry.recipe = chosen
            db.add(entry)
            db.flush()
            entries_by_day_slot[(day, slot)] = entry


def _try_llm_weekly_plan(
    db: Session,
    app_settings: AppSettings,
    req: MealPlanGenerateRequest,
    all_recipes: list[Recipe],
    allowed_diets: set[str],
    excluded_terms: list[str],
    pantry_bonuses: dict[int, float],
    promo_ids: set[int],
) -> tuple[list[tuple[int, str, int, int | None, str | None]] | None, str]:
    """Ask local LLM (Ollama) via strict JSON-Schema to compose the optimal week."""
    client = LocalLlmClient(app_settings)
    health = client.check_health()
    if not health.get("connected"):
        return None, (
            "Lokaler LLM-Server war offline – der Plan wurde direkt mit dem lokalen "
            "Makro- & Budget-Optimierer erstellt."
        )

    # Compact recipe catalog context for fast 24GB-VRAM inference
    catalog_lines = []
    for r in all_recipes:
        if r.diet_type not in allowed_diets or r.effort_level > req.max_effort_level:
            continue
        pantry_flag = " [PANTRY]" if any(ri.ingredient_id in pantry_bonuses for ri in r.ingredients) else ""
        offer_flag = " [ANGEBOT]" if any(ri.ingredient_id in promo_ids for ri in r.ingredients) else ""
        catalog_lines.append(
            f"ID {r.id}: {r.title} | Slots:{r.meal_types_json} | Aufwand:{r.effort_level} | "
            f"{int(r.kcal_per_serving)}kcal P:{int(r.protein_g)}g KH:{int(r.carbs_g)}g "
            f"(Komplex:{int(r.complex_carb_ratio)}%) | ~{r.estimated_cost_per_serving:.2f}€{pantry_flag}{offer_flag}"
        )

    system_prompt = (
        "Du bist ein präziser deutscher Meal-Planning-Experte (Mise-Stil). "
        "Wähle ausschließlich existierende recipe_id aus dem gegebenen Katalog. "
        "Priorisiere hohe Proteinzufuhr, komplexe Kohlenhydrate, Abwechslung, [PANTRY]-Reste "
        "und [ANGEBOT]-Gerichte. "
        f"{_equipment_prompt_rules(app_settings)} "
        "Antworte AUSSCHLIESSLICH als striktes JSON gemäß Schema."
    )
    user_prompt = (
        f"Erstelle einen {req.days_count}-Tage-Wochenplan (day_of_week 0 bis {req.days_count - 1}) "
        f"mit den Slots {req.active_slots} für {req.servings_per_meal} Personen.\n"
        f"Tagesziele pro Person: {app_settings.kcal_target} kcal, {app_settings.protein_g_target}g Protein, "
        f"{app_settings.carbs_g_target}g KH (Fokus komplexe KH), {app_settings.fiber_g_target}g Ballaststoffe.\n"
        f"Batch-Cooking erlaubt: {req.batch_cooking} (du kannst Abendessen als Mittagessen am Folgetag "
        "mit is_leftover_of_day verknüpfen).\n"
        f"Zusatzwunsch: {req.ai_note or 'Kein spezieller Zusatzwunsch'}\n\n"
        "Rezept-Katalog:\n" + "\n".join(catalog_lines[:60])
    )

    try:
        draft = client.generate_structured(
            db=db,
            task_type="weekly_plan",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_cls=LlmWeeklyPlanDraftSchema,
        )
        choices = [
            (s.day_of_week, s.slot, s.recipe_id, s.is_leftover_of_day, s.reason)
            for s in draft.slots
        ]
        return choices, f"KI-Plan ({app_settings.llm_model}): {draft.rationale}"
    except Exception as exc:
        return None, f"KI-Fallback aktiv ({exc}); Plan wurde deterministisch optimiert."


def suggest_swaps_for_entry(
    db: Session, entry: MealPlanEntry, mode: str = "balanced"
) -> list[Recipe]:
    """Return top 6 contextual recipe alternatives for a meal plan slot."""
    app_settings = db.get(AppSettings, 1)
    allowed_diets = DIET_COMPATIBILITY.get(
        app_settings.diet_type if app_settings else "omnivore",
        DIET_COMPATIBILITY["omnivore"],
    )
    pantry_bonuses = _get_pantry_priority_ingredients(db)

    candidates = [
        r
        for r in db.query(Recipe).all()
        if r.id != entry.recipe_id
        and entry.slot in json.loads(r.meal_types_json or "[]")
        and r.diet_type in allowed_diets
    ]

    if mode == "simpler":
        candidates.sort(key=lambda r: (r.effort_level, r.prep_time_min + r.cook_time_min))
    elif mode == "more_protein":
        candidates.sort(key=lambda r: r.protein_g, reverse=True)
    elif mode == "cheaper":
        candidates.sort(key=lambda r: r.estimated_cost_per_serving)
    elif mode == "pantry":
        candidates.sort(
            key=lambda r: sum(pantry_bonuses.get(ri.ingredient_id, 0.0) for ri in r.ingredients),
            reverse=True,
        )
    else:
        candidates.sort(
            key=lambda r: (
                abs(r.kcal_per_serving - entry.recipe.kcal_per_serving) * 0.1
                - r.protein_g * 0.5
                - (r.complex_carb_ratio * 0.1)
            )
        )
    return candidates[:8]


def deduct_pantry_for_cooked_entry(db: Session, entry: MealPlanEntry) -> int:
    """When user marks a meal as cooked, subtract used ingredients from pantry_items."""
    if entry.is_leftover_from_entry_id is not None:
        return 0  # Ingredients already deducted when parent batch-cook was cooked
    recipe = entry.recipe or db.get(Recipe, entry.recipe_id)
    if not recipe:
        return 0
    scale = entry.servings / max(recipe.servings or 1, 1)
    updated_count = 0

    for ri in recipe.ingredients:
        ing = ri.ingredient or db.get(Ingredient, ri.ingredient_id)
        if not ing:
            continue
        used_qty = amount_in_default_unit(ri.amount * scale, ri.unit, ing)
        pantry_rows = (
            db.query(PantryItem)
            .filter(PantryItem.ingredient_id == ing.id, PantryItem.quantity > 0)
            .order_by(PantryItem.expires_at.asc().nullslast())
            .all()
        )
        remaining = used_qty
        for p in pantry_rows:
            if remaining <= 0:
                break
            p_norm = amount_in_default_unit(p.quantity, p.unit, ing)
            if p_norm <= remaining:
                remaining -= p_norm
                p.quantity = 0.0
            else:
                p.quantity = round(p_norm - remaining, 1)
                remaining = 0.0
            updated_count += 1

    db.commit()
    return updated_count


def suggest_recipes_from_pantry(db: Session, limit: int = 8) -> list[dict]:
    """Score recipes by how well they use expiring and available pantry ingredients."""
    pantry_bonuses = _get_pantry_priority_ingredients(db)
    pantry_ids = set(pantry_bonuses.keys())
    if not pantry_ids:
        return []

    results = []
    for recipe in db.query(Recipe).all():
        non_staple_ris = [
            ri for ri in recipe.ingredients if ri.ingredient and not ri.ingredient.is_pantry_staple
        ]
        if not non_staple_ris:
            continue
        matched = [ri for ri in non_staple_ris if ri.ingredient_id in pantry_ids]
        if not matched:
            continue
        coverage = len(matched) / len(non_staple_ris)
        urgency = sum(pantry_bonuses.get(ri.ingredient_id, 0.0) for ri in matched)
        results.append(
            {
                "recipe": recipe,
                "matched_ingredients": [ri.ingredient.name for ri in matched if ri.ingredient],
                "missing_count": len(non_staple_ris) - len(matched),
                "coverage_pct": round(coverage * 100),
                "score": urgency + coverage * 50.0,
            }
        )

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def generate_recipe_with_ai(
    db: Session,
    prompt: str,
    effort_level: int = 1,
    servings: int = 2,
    meal_type: str = "dinner",
    use_pantry: bool = True,
) -> Recipe:
    """Use local LLM (Ollama) with strict JSON-Schema to create a new recipe linked to canonical ingredients."""
    from rapidfuzz import fuzz, process

    app_settings = db.get(AppSettings, 1)
    if not app_settings:
        raise RuntimeError("AppSettings not initialized")

    all_ingredients = db.query(Ingredient).all()
    ing_names = [i.name for i in all_ingredients]
    name_to_ing = {i.name.lower(): i for i in all_ingredients}

    pantry_context = ""
    if use_pantry:
        pantry_rows = db.query(PantryItem).filter(PantryItem.quantity > 0).all()
        if pantry_rows:
            pantry_list = [
                f"{p.ingredient.name} ({int(p.quantity)}{p.unit})"
                for p in pantry_rows
                if p.ingredient
            ]
            pantry_context = f"\nVorhandene Vorräte (gerne verwerten): {', '.join(pantry_list[:20])}"

    effort_desc = {
        1: "Stufe 1 Ultra-Simpel (<=15 Min., wenige Zutaten, 1 Topf/Pfanne oder No-Cook)",
        2: "Stufe 2 Alltagstauglich (15-30 Min., einfach nachzukochen)",
        3: "Stufe 3 Ambitioniert (30-50 Min., besonders raffiniert)",
    }.get(effort_level, "Stufe 2 Alltagstauglich")

    system_prompt = (
        "Du bist ein deutscher Ernährungs- & Koch-Experte. Erstelle ein alltagstaugliches, "
        "super leckeres Rezept mit Fokus auf viel Protein und komplexe Kohlenhydrate (ALDI-Zutaten). "
        f"{_equipment_prompt_rules(app_settings)} "
        "Verwende möglichst die exakten Zutaten-Namen aus der bereitgestellten Liste und gib Mengen "
        "ausschließlich in g, ml oder stk an. Antworte AUSSCHLIESSLICH als striktes JSON gemäß Schema."
    )
    user_prompt = (
        f"Wunsch: {prompt}\n"
        f"Mahlzeit: {meal_type} | Portionen: {servings} | Koch-Einfachheit: {effort_desc}\n"
        f"Ernährungsform: {app_settings.diet_type}{pantry_context}\n\n"
        f"Verfügbare Standard-Zutaten: {', '.join(ing_names)}"
    )

    client = LocalLlmClient(app_settings)
    generated = client.generate_structured(
        db=db,
        task_type="recipe_generation",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        schema_cls=LlmGeneratedRecipeSchema,
    )

    recipe = Recipe(
        title=generated.title,
        description=generated.description,
        servings=generated.servings,
        prep_time_min=generated.prep_time_min,
        cook_time_min=generated.cook_time_min,
        effort_level=generated.effort_level,
        diet_type=generated.diet_type,
        meal_types_json=json.dumps(generated.meal_types, ensure_ascii=False),
        tags_json=json.dumps(list(set(generated.tags + ["ki-rezept"])), ensure_ascii=False),
        instructions_json=json.dumps(generated.instructions, ensure_ascii=False),
        source="llm",
        image_emoji=generated.image_emoji or "✨",
    )
    db.add(recipe)
    db.flush()

    # Map every generated ingredient cleanly to our canonical ingredients table
    for idx, item in enumerate(generated.ingredients):
        lower = item.ingredient_name.strip().lower()
        matched_ing = name_to_ing.get(lower)
        if not matched_ing:
            best = process.extractOne(item.ingredient_name, ing_names, scorer=fuzz.WRatio)
            if best and best[1] >= 72:
                matched_ing = name_to_ing[best[0].lower()]
        if not matched_ing:
            # Create a sensible new ingredient entry so nothing is lost
            slug = f"custom-{abs(hash(lower)) % 1000000}"
            matched_ing = db.query(Ingredient).filter(Ingredient.slug == slug).first()
            if not matched_ing:
                matched_ing = Ingredient(
                    slug=slug,
                    name=item.ingredient_name.strip(),
                    category="Sonstiges",
                    default_unit=item.unit,
                    grams_per_unit=100.0 if item.unit == "stk" else 1.0,
                    kcal_100=120.0,
                    protein_100=6.0,
                    carbs_100=15.0,
                    sugar_100=3.0,
                    fiber_100=2.5,
                    fat_100=3.5,
                    carb_type="mixed",
                    default_pack_size=500.0 if item.unit != "stk" else 4.0,
                    reference_price_eur=1.99,
                    reference_price_per_base_unit=3.98,
                    reference_store="ALDI",
                    nutrition_source="llm_estimate",
                )
                db.add(matched_ing)
                db.flush()

        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=matched_ing.id,
            amount=item.amount,
            unit=item.unit,
            preparation_note=item.preparation_note,
            display_order=idx,
        )
        ri.ingredient = matched_ing
        db.add(ri)
        recipe.ingredients.append(ri)

    recalculate_recipe_metrics(db, recipe)
    db.commit()
    db.refresh(recipe)
    return recipe
