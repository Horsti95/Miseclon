from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import MealPlan, MealPlanEntry, Recipe
from ..schemas import (
    MealPlanEntryUpdate,
    MealPlanGenerateRequest,
    MealPlanOut,
    RecipeOut,
)
from ..services.planner import (
    deduct_pantry_for_cooked_entry,
    generate_meal_plan,
    suggest_swaps_for_entry,
)
from ..services.shopping import rebuild_shopping_list
from .serializers import serialize_meal_plan, serialize_recipe


router = APIRouter(prefix="/api/meal-plans", tags=["meal-plans"])


@router.get("/active", response_model=MealPlanOut)
def get_active_meal_plan(db: Session = Depends(get_db)):
    plan = (
        db.query(MealPlan)
        .filter(MealPlan.status == "active")
        .order_by(MealPlan.id.desc())
        .first()
    )
    if not plan:
        plan = generate_meal_plan(db, MealPlanGenerateRequest())
    return serialize_meal_plan(db, plan)


@router.post("/generate", response_model=MealPlanOut)
def create_generated_plan(
    payload: MealPlanGenerateRequest, db: Session = Depends(get_db)
):
    plan = generate_meal_plan(db, payload)
    return serialize_meal_plan(db, plan)


@router.patch("/{plan_id}/servings", response_model=MealPlanOut)
def update_plan_servings(
    plan_id: int,
    servings: int = Query(ge=1, le=12),
    db: Session = Depends(get_db),
):
    """Scale people count across the entire week in one click and rebuild the shopping list."""
    plan = db.get(MealPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Wochenplan nicht gefunden")

    plan.servings_per_meal = servings
    for entry in plan.entries:
        entry.servings = servings
    db.commit()
    rebuild_shopping_list(db, plan)
    db.refresh(plan)
    return serialize_meal_plan(db, plan)


@router.patch("/entries/{entry_id}", response_model=MealPlanOut)
def update_entry(
    entry_id: int, payload: MealPlanEntryUpdate, db: Session = Depends(get_db)
):
    entry = db.get(MealPlanEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Mahlzeit-Eintrag nicht gefunden")

    was_cooked = entry.is_cooked

    if payload.recipe_id is not None:
        recipe = db.get(Recipe, payload.recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Rezept nicht gefunden")
        entry.recipe_id = recipe.id
        # Swapping breaks an old leftover link if recipes no longer match
        entry.is_leftover_from_entry_id = None
        if payload.notes is None:
            entry.notes = None

    if payload.servings is not None:
        entry.servings = payload.servings
    if payload.notes is not None:
        entry.notes = payload.notes
    if payload.is_cooked is not None:
        entry.is_cooked = payload.is_cooked
        entry.cooked_at = datetime.now(timezone.utc) if payload.is_cooked else None

    db.commit()

    if payload.is_cooked is True and not was_cooked:
        deduct_pantry_for_cooked_entry(db, entry)

    plan = db.get(MealPlan, entry.meal_plan_id)
    if plan:
        rebuild_shopping_list(db, plan)
        db.refresh(plan)
        return serialize_meal_plan(db, plan)
    raise HTTPException(status_code=404, detail="Wochenplan nicht gefunden")


@router.get("/entries/{entry_id}/swaps", response_model=list[RecipeOut])
def get_entry_swaps(
    entry_id: int,
    mode: str = Query(default="balanced"),
    db: Session = Depends(get_db),
):
    entry = db.get(MealPlanEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Mahlzeit-Eintrag nicht gefunden")
    swaps = suggest_swaps_for_entry(db, entry, mode=mode)
    return [serialize_recipe(db, r) for r in swaps]
