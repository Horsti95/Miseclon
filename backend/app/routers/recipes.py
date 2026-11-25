from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Ingredient, Recipe, RecipeIngredient
from ..schemas import RecipeCreate, RecipeOut, RecipeUrlImportRequest
from ..services.nutrition import recalculate_recipe_metrics
from ..services.recipe_importer import import_recipe_from_url
from .serializers import serialize_recipe


router = APIRouter(prefix="/api/recipes", tags=["recipes"])


@router.get("", response_model=list[RecipeOut])
def list_recipes(
    q: str | None = Query(default=None),
    slot: str | None = Query(default=None),
    max_effort: int | None = Query(default=None, ge=1, le=3),
    diet_type: str | None = Query(default=None),
    favorites_only: bool = Query(default=False),
    min_protein: float | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Recipe)
    if max_effort is not None:
        query = query.filter(Recipe.effort_level <= max_effort)
    if favorites_only:
        query = query.filter(Recipe.is_favorite.is_(True))
    if min_protein is not None:
        query = query.filter(Recipe.protein_g >= min_protein)
    if diet_type == "vegan":
        query = query.filter(Recipe.diet_type == "vegan")
    elif diet_type == "vegetarian":
        query = query.filter(Recipe.diet_type.in_(["vegetarian", "vegan"]))
    elif diet_type == "pescatarian":
        query = query.filter(Recipe.diet_type.in_(["pescatarian", "vegetarian", "vegan"]))

    recipes = query.order_by(Recipe.is_favorite.desc(), Recipe.effort_level.asc(), Recipe.title.asc()).all()

    filtered = []
    ql = q.strip().lower() if q else None
    for r in recipes:
        if slot and slot not in json.loads(r.meal_types_json or "[]"):
            continue
        if ql:
            haystack = (
                f"{r.title} {r.description} {r.tags_json} "
                + " ".join(ri.ingredient.name for ri in r.ingredients if ri.ingredient)
            ).lower()
            if ql not in haystack:
                continue
        filtered.append(r)

    return [serialize_recipe(db, r) for r in filtered]


@router.get("/{recipe_id}", response_model=RecipeOut)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    r = db.get(Recipe, recipe_id)
    if not r:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden")
    return serialize_recipe(db, r)


@router.post("", response_model=RecipeOut, status_code=201)
def create_recipe(payload: RecipeCreate, db: Session = Depends(get_db)):
    recipe = Recipe(
        title=payload.title.strip(),
        description=payload.description.strip(),
        servings=payload.servings,
        prep_time_min=payload.prep_time_min,
        cook_time_min=payload.cook_time_min,
        effort_level=payload.effort_level,
        diet_type=payload.diet_type,
        meal_types_json=json.dumps(payload.meal_types, ensure_ascii=False),
        tags_json=json.dumps(payload.tags, ensure_ascii=False),
        instructions_json=json.dumps(payload.instructions, ensure_ascii=False),
        source="manual",
        image_emoji=payload.image_emoji or "🍽️",
    )
    db.add(recipe)
    db.flush()

    for idx, item in enumerate(payload.ingredients):
        ing = db.get(Ingredient, item.ingredient_id)
        if not ing:
            raise HTTPException(status_code=400, detail=f"Zutat ID {item.ingredient_id} nicht gefunden")
        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ing.id,
            amount=item.amount,
            unit=item.unit,
            preparation_note=item.preparation_note,
            is_optional=item.is_optional,
            display_order=idx,
        )
        ri.ingredient = ing
        db.add(ri)
        recipe.ingredients.append(ri)

    recalculate_recipe_metrics(db, recipe)
    db.commit()
    db.refresh(recipe)
    return serialize_recipe(db, recipe)


@router.patch("/{recipe_id}/favorite", response_model=RecipeOut)
def toggle_favorite(recipe_id: int, db: Session = Depends(get_db)):
    r = db.get(Recipe, recipe_id)
    if not r:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden")
    r.is_favorite = not r.is_favorite
    db.commit()
    db.refresh(r)
    return serialize_recipe(db, r)


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    r = db.get(Recipe, recipe_id)
    if not r:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden")
    db.delete(r)
    db.commit()


@router.post("/import-url", response_model=RecipeOut, status_code=201)
def import_url(payload: RecipeUrlImportRequest, db: Session = Depends(get_db)):
    try:
        recipe = import_recipe_from_url(db, payload.url.strip())
        return serialize_recipe(db, recipe)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Rezept konnte nicht von dieser URL geladen werden: {exc}",
        )
