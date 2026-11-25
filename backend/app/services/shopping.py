"""Deterministic consolidated shopping list generator with pantry deduction & pack remainder awareness."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from sqlalchemy.orm import Session

from ..models import (
    AppSettings,
    Ingredient,
    MealPlan,
    PantryItem,
    PriceHistory,
    Recipe,
    ShoppingList,
    ShoppingListItem,
)
from .nutrition import amount_in_default_unit, get_best_unit_price


AISLE_ORDER = [
    "Obst & Gemüse",
    "Fleisch, Fisch & Tofu",
    "Kühlregal & Milch",
    "Backwaren",
    "Trockenwaren & Getreide",
    "Hülsenfrüchte & Konserven",
    "Tiefkühl",
    "Nüsse, Kerne & Samen",
    "Öle, Gewürze & Soßen",
    "Sonstiges",
]


def aisle_sort_key(category: str) -> tuple[int, str]:
    try:
        return (AISLE_ORDER.index(category), category)
    except ValueError:
        return (len(AISLE_ORDER), category)


def _get_pantry_totals(db: Session) -> dict[int, float]:
    """Total available pantry quantities normalized to each ingredient's default_unit."""
    totals: dict[int, float] = defaultdict(float)
    items = db.query(PantryItem).filter(PantryItem.quantity > 0).all()
    for item in items:
        ing = item.ingredient or db.get(Ingredient, item.ingredient_id)
        if not ing:
            continue
        totals[ing.id] += amount_in_default_unit(item.quantity, item.unit, ing)
    return totals


def _compute_needed_by_ingredient(db: Session, plan: MealPlan) -> dict[int, float]:
    """Aggregate all required ingredients for a meal plan in default_unit.

    Leftover entries (is_leftover_from_entry_id != None) are counted via their
    parent entry's total servings (cook-once, eat-twice).
    """
    # Map parent entry id -> count of linked leftover servings so we scale parent cooking once
    extra_servings_by_parent: dict[int, int] = defaultdict(int)
    for entry in plan.entries:
        if entry.is_leftover_from_entry_id:
            extra_servings_by_parent[entry.is_leftover_from_entry_id] += entry.servings

    needed: dict[int, float] = defaultdict(float)
    for entry in plan.entries:
        if entry.is_leftover_from_entry_id is not None:
            continue  # Already accounted for in parent batch-cook entry
        recipe = entry.recipe or db.get(Recipe, entry.recipe_id)
        if not recipe:
            continue
        total_servings_to_cook = entry.servings + extra_servings_by_parent.get(entry.id, 0)
        scale = total_servings_to_cook / max(recipe.servings or 1, 1)

        for ri in recipe.ingredients:
            ing = ri.ingredient or db.get(Ingredient, ri.ingredient_id)
            if not ing:
                continue
            norm_amount = amount_in_default_unit(ri.amount * scale, ri.unit, ing)
            needed[ing.id] += norm_amount

    return needed


def rebuild_shopping_list(db: Session, plan: MealPlan) -> ShoppingList:
    """Create or deterministically refresh the consolidated shopping list for a meal plan.

    Preserves manual additions and user-checked states / actual prices for existing ingredients.
    """
    app_settings = db.get(AppSettings, 1)
    max_stores = app_settings.max_stores_per_trip if app_settings else 1
    primary_store = "ALDI"

    shopping_list = (
        db.query(ShoppingList).filter(ShoppingList.meal_plan_id == plan.id).first()
    )
    existing_state: dict[int, tuple[bool, float | None, bool]] = {}
    manual_items: list[ShoppingListItem] = []

    if shopping_list:
        for item in list(shopping_list.items):
            if item.manual_addition:
                manual_items.append(item)
            else:
                if item.ingredient_id:
                    existing_state[item.ingredient_id] = (
                        item.is_checked,
                        item.actual_price_eur,
                        item.added_to_pantry,
                    )
                db.delete(item)
        db.flush()
    else:
        shopping_list = ShoppingList(meal_plan_id=plan.id, status="open")
        db.add(shopping_list)
        db.flush()

    needed_map = _compute_needed_by_ingredient(db, plan)
    pantry_map = _get_pantry_totals(db)

    total_estimated = 0.0
    for ing_id, needed_amount in needed_map.items():
        ing = db.get(Ingredient, ing_id)
        if not ing:
            continue

        available = pantry_map.get(ing_id, 0.0)
        deducted = min(available, needed_amount)
        to_buy = max(needed_amount - deducted, 0.0)

        # Skip tiny pantry staple amounts already covered or negligible (< 1g salt etc.)
        if to_buy <= 0.01:
            continue

        per_unit_price, confidence, store_name, selected_offer = get_best_unit_price(
            db, ing
        )

        # Respect 1-store preference: if user wants 1-stop shopping at ALDI, keep promo only if it matches ALDI
        if max_stores == 1 and confidence == "promo" and "aldi" not in store_name.lower():
            pack_ref = ing.default_pack_size if ing.default_pack_size > 0 else 100.0
            per_unit_price = ing.reference_price_eur / pack_ref
            confidence = "estimated"
            store_name = ing.reference_store or primary_store
            selected_offer = None

        # Determine realistic pack size (from offer if available, else ALDI default)
        if (
            selected_offer
            and selected_offer.pack_size_value
            and selected_offer.pack_size_value > 0
        ):
            pack_size = amount_in_default_unit(
                selected_offer.pack_size_value,
                selected_offer.pack_size_unit or ing.default_unit,
                ing,
            )
            pack_price = selected_offer.price_eur
        else:
            pack_size = ing.default_pack_size if ing.default_pack_size > 0 else to_buy
            pack_price = (
                ing.reference_price_eur
                if confidence == "estimated"
                else round(pack_size * per_unit_price, 2)
            )

        pack_count = max(1, math.ceil(to_buy / max(pack_size, 1.0)))
        bought_total = pack_count * pack_size
        remainder = max(round(bought_total - to_buy, 1), 0.0)

        # For long-life staples (oil, spices, honey), price proportionally to pack_count only when bought
        estimated_cost = round(pack_count * pack_price, 2)
        total_estimated += estimated_cost

        prev_checked, prev_actual, prev_added = existing_state.get(
            ing_id, (False, None, False)
        )

        db.add(
            ShoppingListItem(
                shopping_list_id=shopping_list.id,
                ingredient_id=ing.id,
                custom_name=ing.name,
                category=ing.category,
                needed_amount=round(needed_amount, 1),
                pantry_deducted_amount=round(deducted, 1),
                to_buy_amount=round(to_buy, 1),
                unit=ing.default_unit,
                pack_size=round(pack_size, 1),
                suggested_pack_count=pack_count,
                remainder_amount=remainder,
                selected_offer_id=selected_offer.id if selected_offer else None,
                assigned_store_name=store_name,
                estimated_price_eur=estimated_cost,
                actual_price_eur=prev_actual,
                price_confidence=confidence,
                is_checked=prev_checked,
                added_to_pantry=prev_added,
                manual_addition=False,
            )
        )

    for m in manual_items:
        total_estimated += m.estimated_price_eur

    plan.estimated_cost_eur = round(total_estimated, 2)
    db.commit()
    db.refresh(shopping_list)
    return shopping_list


def record_actual_price_to_history(db: Session, item: ShoppingListItem) -> None:
    """Save user-entered real checkout price into price_history for future verified estimates."""
    if not item.ingredient_id or item.actual_price_eur is None or item.actual_price_eur <= 0:
        return
    ing = db.get(Ingredient, item.ingredient_id)
    if not ing:
        return
    total_qty = max(item.pack_size * max(item.suggested_pack_count, 1), item.to_buy_amount, 1.0)
    if ing.default_unit in ("g", "ml"):
        base_price = round(item.actual_price_eur / (total_qty / 1000.0), 2)
    else:
        base_price = round(item.actual_price_eur / total_qty, 2)

    db.add(
        PriceHistory(
            ingredient_id=ing.id,
            store_name=item.assigned_store_name or "ALDI",
            price_eur=round(item.actual_price_eur / max(item.suggested_pack_count, 1), 2),
            pack_size_value=item.pack_size if item.pack_size > 0 else total_qty,
            pack_size_unit=ing.default_unit,
            base_price_eur=base_price,
            source="user_purchase",
        )
    )


def move_checked_items_to_pantry(db: Session, shopping_list: ShoppingList) -> int:
    """Add all checked shopping list items (not yet transferred) into pantry_items."""
    moved = 0
    for item in shopping_list.items:
        if not item.is_checked or item.added_to_pantry or not item.ingredient_id:
            continue
        ing = db.get(Ingredient, item.ingredient_id)
        if not ing:
            continue

        add_qty = (
            item.pack_size * item.suggested_pack_count
            if item.pack_size > 0
            else item.to_buy_amount
        )
        location = "pantry"
        if ing.category in ("Kühlregal & Milch", "Fleisch, Fisch & Tofu", "Obst & Gemüse"):
            location = "fridge"
        elif ing.category == "Tiefkühl":
            location = "freezer"

        expires_at = (
            date.today() + timedelta(days=ing.default_shelf_life_days)
        ).isoformat()

        existing = (
            db.query(PantryItem)
            .filter(
                PantryItem.ingredient_id == ing.id,
                PantryItem.location == location,
            )
            .first()
        )
        if existing:
            existing.quantity = round(existing.quantity + add_qty, 1)
            existing.expires_at = expires_at
        else:
            db.add(
                PantryItem(
                    ingredient_id=ing.id,
                    quantity=round(add_qty, 1),
                    unit=ing.default_unit,
                    location=location,
                    expires_at=expires_at,
                    use_priority="normal",
                    notes="Aus Einkaufsliste übernommen",
                )
            )
        item.added_to_pantry = True
        moved += 1

    db.commit()
    return moved


def get_pack_remainder_suggestions(
    db: Session, shopping_list: ShoppingList, plan: MealPlan
) -> list[dict]:
    """Identify significant fresh-food pack remainders and suggest recipes using them."""
    used_recipe_ids = {e.recipe_id for e in plan.entries}
    fresh_categories = {"Obst & Gemüse", "Kühlregal & Milch", "Fleisch, Fisch & Tofu"}

    remainders = [
        item
        for item in shopping_list.items
        if item.ingredient_id
        and not item.manual_addition
        and item.category in fresh_categories
        and item.pack_size > 0
        and item.remainder_amount >= max(item.pack_size * 0.25, 50.0)
    ]
    if not remainders:
        return []

    remainders.sort(key=lambda i: i.remainder_amount, reverse=True)
    suggestions: list[dict] = []
    all_recipes = db.query(Recipe).all()

    for rem in remainders[:4]:
        matching = []
        for r in all_recipes:
            if r.id in used_recipe_ids:
                continue
            if any(ri.ingredient_id == rem.ingredient_id for ri in r.ingredients):
                matching.append(
                    {
                        "recipe_id": r.id,
                        "title": r.title,
                        "effort_level": r.effort_level,
                        "kcal_per_serving": r.kcal_per_serving,
                        "protein_g": r.protein_g,
                    }
                )
        if matching:
            suggestions.append(
                {
                    "ingredient_id": rem.ingredient_id,
                    "ingredient_name": rem.custom_name,
                    "remainder_amount": rem.remainder_amount,
                    "unit": rem.unit,
                    "suggested_recipes": matching[:2],
                }
            )
    return suggestions
