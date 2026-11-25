"""Deterministic nutrition, unit-conversion, and price-calculation engine."""

from __future__ import annotations

from datetime import date
from sqlalchemy.orm import Session

from ..models import Ingredient, IngredientOfferMatch, PriceHistory, PriceOffer, Recipe


EFFORT_LABELS = {
    1: "Ultra-Simpel",
    2: "Alltagstauglich",
    3: "Ambitioniert",
}

DAY_LABELS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def amount_to_grams(amount: float, unit: str, ingredient: Ingredient) -> float:
    """Convert any recipe ingredient quantity to grams/ml equivalent for nutrition math."""
    u = (unit or ingredient.default_unit or "g").lower().strip()
    if u in ("g", "ml"):
        return float(amount)
    if u == "kg":
        return float(amount) * 1000.0
    if u == "l":
        return float(amount) * 1000.0
    if u == "stk":
        gpu = ingredient.grams_per_unit if ingredient.grams_per_unit and ingredient.grams_per_unit > 0 else 100.0
        return float(amount) * gpu
    return float(amount)


def amount_in_default_unit(amount: float, unit: str, ingredient: Ingredient) -> float:
    """Normalize an amount into the ingredient's canonical default_unit."""
    u = (unit or ingredient.default_unit or "g").lower().strip()
    target = (ingredient.default_unit or "g").lower().strip()
    if u == target:
        return float(amount)
    if u == "kg" and target == "g":
        return float(amount) * 1000.0
    if u == "l" and target == "ml":
        return float(amount) * 1000.0
    grams = amount_to_grams(amount, u, ingredient)
    if target in ("g", "ml"):
        return grams
    if target == "stk":
        gpu = ingredient.grams_per_unit if ingredient.grams_per_unit > 0 else 100.0
        return grams / gpu
    return float(amount)


def get_best_unit_price(
    db: Session,
    ingredient: Ingredient,
    preferred_chains: list[str] | None = None,
) -> tuple[float, str, str, PriceOffer | None]:
    """Resolve price per ingredient default_unit following 3-layer fallback:

    1. Active weekly promo offer (not rejected, valid_to >= today or null)
    2. Latest verified user purchase price from price_history
    3. Curated ALDI reference price on Ingredient

    Returns: (price_per_default_unit, confidence, store_name, selected_offer)
    """
    today_str = date.today().isoformat()

    # Layer 1: Active matched promo offers
    matches = (
        db.query(IngredientOfferMatch, PriceOffer)
        .join(PriceOffer, IngredientOfferMatch.offer_id == PriceOffer.id)
        .filter(
            IngredientOfferMatch.ingredient_id == ingredient.id,
            IngredientOfferMatch.is_rejected.is_(False),
            IngredientOfferMatch.confidence >= 0.60,
        )
        .all()
    )

    best_offer: PriceOffer | None = None
    best_per_unit: float | None = None
    for _match, offer in matches:
        if offer.valid_to and offer.valid_to < today_str:
            continue
        if offer.base_price_eur and offer.base_price_eur > 0:
            if ingredient.default_unit in ("g", "ml") and offer.base_unit in ("kg", "l"):
                per_unit = offer.base_price_eur / 1000.0
            elif ingredient.default_unit == "stk" and offer.base_unit == "stk":
                per_unit = offer.base_price_eur
            elif offer.pack_size_value and offer.pack_size_value > 0:
                norm_pack = amount_in_default_unit(
                    offer.pack_size_value, offer.pack_size_unit or ingredient.default_unit, ingredient
                )
                per_unit = offer.price_eur / max(norm_pack, 1.0)
            else:
                per_unit = offer.price_eur / max(ingredient.default_pack_size, 1.0)
        else:
            per_unit = offer.price_eur / max(ingredient.default_pack_size, 1.0)

        if best_per_unit is None or per_unit < best_per_unit:
            best_per_unit = per_unit
            best_offer = offer

    if best_offer is not None and best_per_unit is not None:
        return best_per_unit, "promo", best_offer.store_name, best_offer

    # Layer 2: Verified user purchase history
    latest_verified = (
        db.query(PriceHistory)
        .filter(
            PriceHistory.ingredient_id == ingredient.id,
            PriceHistory.source == "user_purchase",
        )
        .order_by(PriceHistory.recorded_at.desc())
        .first()
    )
    if latest_verified and latest_verified.pack_size_value > 0:
        norm_pack = amount_in_default_unit(
            latest_verified.pack_size_value, latest_verified.pack_size_unit, ingredient
        )
        per_unit = latest_verified.price_eur / max(norm_pack, 1.0)
        return per_unit, "verified", latest_verified.store_name, None

    # Layer 3: ALDI curated baseline
    pack = ingredient.default_pack_size if ingredient.default_pack_size > 0 else 100.0
    per_unit = ingredient.reference_price_eur / pack
    return per_unit, "estimated", ingredient.reference_store or "ALDI", None


def compute_ingredient_cost(
    db: Session, ingredient: Ingredient, amount: float, unit: str
) -> float:
    norm_amount = amount_in_default_unit(amount, unit, ingredient)
    per_unit, _, _, _ = get_best_unit_price(db, ingredient)
    return round(norm_amount * per_unit, 2)


def recalculate_recipe_metrics(db: Session, recipe: Recipe) -> Recipe:
    """Deterministically calculate per-serving macros, complex carb ratio, and ALDI cost."""
    total_kcal = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_sugar = 0.0
    total_fiber = 0.0
    total_fat = 0.0
    complex_carbs = 0.0
    total_cost = 0.0

    for ri in recipe.ingredients:
        ing = ri.ingredient or db.get(Ingredient, ri.ingredient_id)
        if not ing:
            continue
        grams = amount_to_grams(ri.amount, ri.unit, ing)
        factor = grams / 100.0

        total_kcal += ing.kcal_100 * factor
        total_protein += ing.protein_100 * factor
        ing_carbs = ing.carbs_100 * factor
        total_carbs += ing_carbs
        total_sugar += ing.sugar_100 * factor
        total_fiber += ing.fiber_100 * factor
        total_fat += ing.fat_100 * factor

        if ing.carb_type == "complex":
            complex_carbs += ing_carbs
        elif ing.carb_type == "mixed":
            complex_carbs += ing_carbs * 0.5

        norm_amount = amount_in_default_unit(ri.amount, ri.unit, ing)
        pack = ing.default_pack_size if ing.default_pack_size > 0 else 100.0
        total_cost += norm_amount * (ing.reference_price_eur / pack)

    servings = max(recipe.servings or 1, 1)
    recipe.kcal_per_serving = round(total_kcal / servings, 1)
    recipe.protein_g = round(total_protein / servings, 1)
    recipe.carbs_g = round(total_carbs / servings, 1)
    recipe.sugar_g = round(total_sugar / servings, 1)
    recipe.fiber_g = round(total_fiber / servings, 1)
    recipe.fat_g = round(total_fat / servings, 1)
    recipe.complex_carb_ratio = (
        round(min(complex_carbs / total_carbs, 1.0) * 100.0, 1)
        if total_carbs > 1.0
        else 100.0
    )
    recipe.estimated_cost_per_serving = round(total_cost / servings, 2)
    recipe.macros_verified = True
    return recipe
