"""Shared ORM-to-Pydantic serializers."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from sqlalchemy.orm import Session

from ..models import (
    AppSettings,
    Ingredient,
    MealPlan,
    PantryItem,
    Recipe,
    ShoppingList,
)
from ..schemas import (
    DayMacroSummary,
    MealPlanEntryOut,
    MealPlanOut,
    PantryItemOut,
    RecipeIngredientOut,
    RecipeOut,
    SettingsOut,
    ShoppingListItemOut,
    ShoppingListOut,
)
from ..services.nutrition import (
    DAY_LABELS,
    EFFORT_LABELS,
    amount_in_default_unit,
    get_best_unit_price,
)
from ..services.shopping import aisle_sort_key, get_pack_remainder_suggestions


def serialize_settings(s: AppSettings) -> SettingsOut:
    return SettingsOut(
        postal_code=s.postal_code,
        primary_store_chain=s.primary_store_chain,
        enabled_stores=json.loads(s.enabled_stores_json or "[]"),
        default_servings=s.default_servings,
        default_days=s.default_days,
        default_max_effort=s.default_max_effort,
        weekly_budget_eur=s.weekly_budget_eur,
        kcal_target=s.kcal_target,
        protein_g_target=s.protein_g_target,
        carbs_g_target=s.carbs_g_target,
        fiber_g_target=s.fiber_g_target,
        fat_g_target=s.fat_g_target,
        prefer_complex_carbs=s.prefer_complex_carbs,
        diet_type=s.diet_type,
        excluded_ingredients=json.loads(s.excluded_ingredients_json or "[]"),
        kitchen_equipment=json.loads(
            s.kitchen_equipment_json or '["airfryer", "stove_2_burners", "oven"]'
        ),
        max_stores_per_trip=s.max_stores_per_trip,
        llm_base_url=s.llm_base_url,
        llm_model=s.llm_model,
        llm_api_key=s.llm_api_key,
        llm_temperature=s.llm_temperature,
        auto_sync_offers_on_start=s.auto_sync_offers_on_start,
    )


def serialize_recipe(db: Session, r: Recipe) -> RecipeOut:
    ing_outs: list[RecipeIngredientOut] = []
    for ri in r.ingredients:
        ing = ri.ingredient or db.get(Ingredient, ri.ingredient_id)
        if not ing:
            continue
        norm_amount = amount_in_default_unit(ri.amount, ri.unit, ing)
        pack = ing.default_pack_size if ing.default_pack_size > 0 else 100.0
        est_cost = round(norm_amount * (ing.reference_price_eur / pack), 2)
        ing_outs.append(
            RecipeIngredientOut(
                id=ri.id,
                ingredient_id=ing.id,
                ingredient_name=ing.name,
                category=ing.category,
                amount=round(ri.amount, 1),
                unit=ri.unit,
                preparation_note=ri.preparation_note,
                is_optional=ri.is_optional,
                carb_type=ing.carb_type,
                estimated_cost_eur=est_cost,
            )
        )

    return RecipeOut(
        id=r.id,
        slug=r.slug,
        title=r.title,
        description=r.description,
        servings=r.servings,
        prep_time_min=r.prep_time_min,
        cook_time_min=r.cook_time_min,
        total_time_min=r.prep_time_min + r.cook_time_min,
        effort_level=r.effort_level,
        effort_label=EFFORT_LABELS.get(r.effort_level, "Alltagstauglich"),
        diet_type=r.diet_type,
        meal_types=json.loads(r.meal_types_json or "[]"),
        tags=json.loads(r.tags_json or "[]"),
        instructions=json.loads(r.instructions_json or "[]"),
        source=r.source,
        source_url=r.source_url,
        is_favorite=r.is_favorite,
        rating=r.rating,
        image_emoji=r.image_emoji or "🍽️",
        kcal_per_serving=round(r.kcal_per_serving, 1),
        protein_g=round(r.protein_g, 1),
        carbs_g=round(r.carbs_g, 1),
        sugar_g=round(r.sugar_g, 1),
        fiber_g=round(r.fiber_g, 1),
        fat_g=round(r.fat_g, 1),
        complex_carb_ratio=round(r.complex_carb_ratio, 1),
        estimated_cost_per_serving=round(r.estimated_cost_per_serving, 2),
        macros_verified=r.macros_verified,
        ingredients=ing_outs,
    )


def serialize_pantry_item(item: PantryItem) -> PantryItemOut:
    days_left = None
    if item.expires_at:
        try:
            exp = date.fromisoformat(item.expires_at[:10])
            days_left = (exp - date.today()).days
        except ValueError:
            pass

    return PantryItemOut(
        id=item.id,
        ingredient_id=item.ingredient_id,
        ingredient_name=item.ingredient.name if item.ingredient else "Zutat",
        category=item.ingredient.category if item.ingredient else "Sonstiges",
        quantity=round(item.quantity, 1),
        unit=item.unit,
        location=item.location,
        opened_at=item.opened_at,
        expires_at=item.expires_at,
        days_until_expiry=days_left,
        use_priority=item.use_priority,
        notes=item.notes,
    )


def serialize_meal_plan(db: Session, plan: MealPlan) -> MealPlanOut:
    slot_order = {"breakfast": 0, "lunch": 1, "dinner": 2, "snack": 3}
    sorted_entries = sorted(
        plan.entries, key=lambda e: (e.day_of_week, slot_order.get(e.slot, 9), e.id)
    )

    recipe_cache: dict[int, RecipeOut] = {}
    entries_out: list[MealPlanEntryOut] = []
    daily_buckets: dict[int, list[MealPlanEntryOut]] = defaultdict(list)

    for e in sorted_entries:
        if e.recipe_id not in recipe_cache:
            recipe_cache[e.recipe_id] = serialize_recipe(db, e.recipe)
        e_out = MealPlanEntryOut(
            id=e.id,
            day_of_week=e.day_of_week,
            day_label=DAY_LABELS[e.day_of_week] if 0 <= e.day_of_week < 7 else f"Tag {e.day_of_week + 1}",
            slot=e.slot,
            servings=e.servings,
            is_leftover_from_entry_id=e.is_leftover_from_entry_id,
            is_cooked=e.is_cooked,
            notes=e.notes,
            recipe=recipe_cache[e.recipe_id],
        )
        entries_out.append(e_out)
        daily_buckets[e.day_of_week].append(e_out)

    daily_macros: list[DayMacroSummary] = []
    for day in range(plan.days_count):
        day_entries = daily_buckets.get(day, [])
        kcal = sum(e.recipe.kcal_per_serving for e in day_entries)
        prot = sum(e.recipe.protein_g for e in day_entries)
        carbs = sum(e.recipe.carbs_g for e in day_entries)
        sugar = sum(e.recipe.sugar_g for e in day_entries)
        fiber = sum(e.recipe.fiber_g for e in day_entries)
        fat = sum(e.recipe.fat_g for e in day_entries)
        cost_pp = sum(e.recipe.estimated_cost_per_serving for e in day_entries)
        cost_tot = sum(e.recipe.estimated_cost_per_serving * e.servings for e in day_entries)
        if carbs > 0.5:
            weighted_complex = sum(
                e.recipe.carbs_g * (e.recipe.complex_carb_ratio / 100.0)
                for e in day_entries
            )
            complex_ratio = round(min(weighted_complex / carbs, 1.0) * 100.0, 1)
        else:
            complex_ratio = 100.0

        daily_macros.append(
            DayMacroSummary(
                day_of_week=day,
                day_label=DAY_LABELS[day] if day < 7 else f"Tag {day + 1}",
                kcal=round(kcal, 0),
                protein_g=round(prot, 1),
                carbs_g=round(carbs, 1),
                sugar_g=round(sugar, 1),
                fiber_g=round(fiber, 1),
                fat_g=round(fat, 1),
                complex_carb_ratio=complex_ratio,
                estimated_cost_per_person=round(cost_pp, 2),
                estimated_cost_total=round(cost_tot, 2),
                meals_count=len(day_entries),
                cooked_count=sum(1 for e in day_entries if e.is_cooked),
            )
        )

    n_days = max(len(daily_macros), 1)
    sl = db.query(ShoppingList).filter(ShoppingList.meal_plan_id == plan.id).first()
    shopping_cost = (
        round(sum(i.actual_price_eur if i.actual_price_eur is not None else i.estimated_price_eur for i in sl.items), 2)
        if sl
        else plan.estimated_cost_eur
    )
    recipe_sum_cost = round(sum(d.estimated_cost_total for d in daily_macros), 2)

    return MealPlanOut(
        id=plan.id,
        title=plan.title,
        week_start_date=plan.week_start_date,
        days_count=plan.days_count,
        servings_per_meal=plan.servings_per_meal,
        max_effort_level=plan.max_effort_level,
        target_budget_eur=plan.target_budget_eur,
        active_slots=json.loads(plan.active_slots_json or "[]"),
        batch_cooking=plan.batch_cooking,
        status=plan.status,
        estimated_cost_eur=recipe_sum_cost,
        shopping_cost_after_pantry_eur=shopping_cost,
        llm_rationale=plan.llm_rationale,
        entries=entries_out,
        daily_macros=daily_macros,
        weekly_avg_kcal=round(sum(d.kcal for d in daily_macros) / n_days, 0),
        weekly_avg_protein_g=round(sum(d.protein_g for d in daily_macros) / n_days, 1),
        weekly_avg_carbs_g=round(sum(d.carbs_g for d in daily_macros) / n_days, 1),
        weekly_avg_fiber_g=round(sum(d.fiber_g for d in daily_macros) / n_days, 1),
        weekly_avg_fat_g=round(sum(d.fat_g for d in daily_macros) / n_days, 1),
        weekly_avg_complex_carb_ratio=round(
            sum(d.complex_carb_ratio for d in daily_macros) / n_days, 1
        ),
    )


def serialize_shopping_list(db: Session, sl: ShoppingList, plan: MealPlan) -> ShoppingListOut:
    sorted_items = sorted(
        sl.items,
        key=lambda i: (aisle_sort_key(i.category), i.custom_name.lower()),
    )

    items_out: list[ShoppingListItemOut] = []
    store_breakdown: dict[str, float] = defaultdict(float)
    promo_count = 0
    verified_count = 0
    estimated_count = 0
    total_est = 0.0
    total_act = 0.0

    for item in sorted_items:
        price = item.actual_price_eur if item.actual_price_eur is not None else item.estimated_price_eur
        total_est += item.estimated_price_eur
        total_act += price
        store_breakdown[item.assigned_store_name] = round(
            store_breakdown[item.assigned_store_name] + price, 2
        )
        if item.price_confidence == "promo":
            promo_count += 1
        elif item.price_confidence == "verified":
            verified_count += 1
        else:
            estimated_count += 1

        items_out.append(
            ShoppingListItemOut(
                id=item.id,
                ingredient_id=item.ingredient_id,
                custom_name=item.custom_name,
                category=item.category,
                needed_amount=round(item.needed_amount, 1),
                pantry_deducted_amount=round(item.pantry_deducted_amount, 1),
                to_buy_amount=round(item.to_buy_amount, 1),
                unit=item.unit,
                pack_size=round(item.pack_size, 1),
                suggested_pack_count=item.suggested_pack_count,
                remainder_amount=round(item.remainder_amount, 1),
                assigned_store_name=item.assigned_store_name,
                estimated_price_eur=round(item.estimated_price_eur, 2),
                actual_price_eur=item.actual_price_eur,
                price_confidence=item.price_confidence,
                offer_title=item.selected_offer.raw_title if item.selected_offer else None,
                offer_valid_to=item.selected_offer.valid_to if item.selected_offer else None,
                is_checked=item.is_checked,
                added_to_pantry=item.added_to_pantry,
                manual_addition=item.manual_addition,
            )
        )

    remainder_suggestions = get_pack_remainder_suggestions(db, sl, plan)

    return ShoppingListOut(
        id=sl.id,
        meal_plan_id=sl.meal_plan_id,
        status=sl.status,
        total_estimated_eur=round(total_est, 2),
        total_actual_eur=round(total_act, 2),
        promo_items_count=promo_count,
        verified_items_count=verified_count,
        estimated_items_count=estimated_count,
        checked_count=sum(1 for i in items_out if i.is_checked),
        total_items_count=len(items_out),
        store_breakdown=dict(store_breakdown),
        remainder_suggestions=remainder_suggestions,
        items=items_out,
    )
