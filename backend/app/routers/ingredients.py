from __future__ import annotations

import re
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Ingredient, MealPlan, PriceHistory, Recipe
from ..schemas import IngredientCreate, IngredientOut, IngredientPriceUpdate
from ..services.nutrition import get_best_unit_price, recalculate_recipe_metrics
from ..services.recipe_importer import search_openfoodfacts
from ..services.shopping import rebuild_shopping_list


router = APIRouter(prefix="/api/ingredients", tags=["ingredients"])


def _serialize_ingredient(db: Session, ing: Ingredient) -> IngredientOut:
    per_unit, conf, store_name, offer = get_best_unit_price(db, ing)
    return IngredientOut(
        id=ing.id,
        slug=ing.slug,
        name=ing.name,
        category=ing.category,
        default_unit=ing.default_unit,
        grams_per_unit=ing.grams_per_unit,
        kcal_100=ing.kcal_100,
        protein_100=ing.protein_100,
        carbs_100=ing.carbs_100,
        sugar_100=ing.sugar_100,
        fiber_100=ing.fiber_100,
        fat_100=ing.fat_100,
        carb_type=ing.carb_type,
        is_pantry_staple=ing.is_pantry_staple,
        default_shelf_life_days=ing.default_shelf_life_days,
        default_pack_size=ing.default_pack_size,
        reference_price_eur=round(ing.reference_price_eur, 2),
        reference_price_per_base_unit=round(ing.reference_price_per_base_unit, 2),
        reference_store=ing.reference_store,
        nutrition_source=ing.nutrition_source,
        active_offer_price=offer.price_eur if offer else None,
        active_offer_store=store_name if conf == "promo" else None,
    )


@router.get("", response_model=list[IngredientOut])
def list_ingredients(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    carb_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Ingredient)
    if category:
        query = query.filter(Ingredient.category == category)
    if carb_type:
        query = query.filter(Ingredient.carb_type == carb_type)
    items = query.order_by(Ingredient.category.asc(), Ingredient.name.asc()).all()
    if q:
        ql = q.strip().lower()
        items = [i for i in items if ql in i.name.lower() or ql in i.category.lower()]
    return [_serialize_ingredient(db, i) for i in items]


@router.post("", response_model=IngredientOut, status_code=201)
def create_ingredient(payload: IngredientCreate, db: Session = Depends(get_db)):
    base_slug = re.sub(r"[^a-z0-9]+", "-", payload.name.lower()).strip("-") or "zutat"
    slug = base_slug
    counter = 1
    while db.query(Ingredient).filter(Ingredient.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    if payload.default_unit in ("g", "ml"):
        base_price = round(payload.reference_price_eur / (payload.default_pack_size / 1000.0), 2)
    else:
        base_price = round(payload.reference_price_eur / payload.default_pack_size, 2)

    ing = Ingredient(
        slug=slug,
        name=payload.name.strip(),
        category=payload.category,
        default_unit=payload.default_unit,
        grams_per_unit=payload.grams_per_unit,
        kcal_100=payload.kcal_100,
        protein_100=payload.protein_100,
        carbs_100=payload.carbs_100,
        sugar_100=payload.sugar_100,
        fiber_100=payload.fiber_100,
        fat_100=payload.fat_100,
        carb_type=payload.carb_type,
        is_pantry_staple=payload.is_pantry_staple,
        default_shelf_life_days=payload.default_shelf_life_days,
        default_pack_size=payload.default_pack_size,
        reference_price_eur=payload.reference_price_eur,
        reference_price_per_base_unit=base_price,
        reference_store=payload.reference_store,
        nutrition_source="user",
    )
    db.add(ing)
    db.commit()
    db.refresh(ing)
    return _serialize_ingredient(db, ing)


@router.patch("/{ingredient_id}/price", response_model=IngredientOut)
def update_ingredient_price(
    ingredient_id: int, payload: IngredientPriceUpdate, db: Session = Depends(get_db)
):
    ing = db.get(Ingredient, ingredient_id)
    if not ing:
        raise HTTPException(status_code=404, detail="Zutat nicht gefunden")

    ing.reference_price_eur = payload.reference_price_eur
    if payload.default_pack_size:
        ing.default_pack_size = payload.default_pack_size
    if payload.reference_store:
        ing.reference_store = payload.reference_store

    if ing.default_unit in ("g", "ml"):
        ing.reference_price_per_base_unit = round(
            ing.reference_price_eur / (ing.default_pack_size / 1000.0), 2
        )
    else:
        ing.reference_price_per_base_unit = round(
            ing.reference_price_eur / max(ing.default_pack_size, 1.0), 2
        )

    db.add(
        PriceHistory(
            ingredient_id=ing.id,
            store_name=ing.reference_store,
            price_eur=ing.reference_price_eur,
            pack_size_value=ing.default_pack_size,
            pack_size_unit=ing.default_unit,
            base_price_eur=ing.reference_price_per_base_unit,
            source="manual",
        )
    )

    # Recalculate affected recipes & active shopping list
    affected_recipes = (
        db.query(Recipe)
        .filter(Recipe.ingredients.any(ingredient_id=ing.id))
        .all()
    )
    for r in affected_recipes:
        recalculate_recipe_metrics(db, r)

    db.commit()
    active_plan = db.query(MealPlan).filter(MealPlan.status == "active").first()
    if active_plan:
        rebuild_shopping_list(db, active_plan)

    db.refresh(ing)
    return _serialize_ingredient(db, ing)


@router.get("/openfoodfacts")
def openfoodfacts_lookup(q: str = Query(min_length=2)):
    try:
        return search_openfoodfacts(q)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OpenFoodFacts-Suche derzeit nicht erreichbar: {exc}",
        )
