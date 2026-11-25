from __future__ import annotations

from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Ingredient, MealPlan, PantryItem
from ..schemas import PantryItemCreate, PantryItemOut, PantryItemUpdate
from ..services.planner import suggest_recipes_from_pantry
from ..services.shopping import rebuild_shopping_list
from .serializers import serialize_pantry_item, serialize_recipe


router = APIRouter(prefix="/api/pantry", tags=["pantry"])


@router.get("", response_model=list[PantryItemOut])
def list_pantry(db: Session = Depends(get_db)):
    items = (
        db.query(PantryItem)
        .filter(PantryItem.quantity > 0)
        .order_by(PantryItem.expires_at.asc().nullslast(), PantryItem.id.desc())
        .all()
    )
    return [serialize_pantry_item(i) for i in items]


@router.post("", response_model=PantryItemOut, status_code=201)
def add_pantry_item(payload: PantryItemCreate, db: Session = Depends(get_db)):
    ing = db.get(Ingredient, payload.ingredient_id)
    if not ing:
        raise HTTPException(status_code=404, detail="Zutat nicht gefunden")

    unit = payload.unit or ing.default_unit
    expires_at = payload.expires_at
    if not expires_at:
        expires_at = (
            date.today() + timedelta(days=ing.default_shelf_life_days)
        ).isoformat()

    existing = (
        db.query(PantryItem)
        .filter(
            PantryItem.ingredient_id == ing.id,
            PantryItem.location == payload.location,
        )
        .first()
    )
    if existing:
        existing.quantity = round(existing.quantity + payload.quantity, 1)
        existing.expires_at = expires_at
        existing.use_priority = payload.use_priority
        if payload.notes:
            existing.notes = payload.notes
        item = existing
    else:
        item = PantryItem(
            ingredient_id=ing.id,
            quantity=round(payload.quantity, 1),
            unit=unit,
            location=payload.location,
            expires_at=expires_at,
            use_priority=payload.use_priority,
            notes=payload.notes,
        )
        db.add(item)

    db.commit()
    db.refresh(item)

    active_plan = db.query(MealPlan).filter(MealPlan.status == "active").first()
    if active_plan:
        rebuild_shopping_list(db, active_plan)

    return serialize_pantry_item(item)


@router.patch("/{item_id}", response_model=PantryItemOut)
def update_pantry_item(
    item_id: int, payload: PantryItemUpdate, db: Session = Depends(get_db)
):
    item = db.get(PantryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Vorratseintrag nicht gefunden")

    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)

    active_plan = db.query(MealPlan).filter(MealPlan.status == "active").first()
    if active_plan:
        rebuild_shopping_list(db, active_plan)

    return serialize_pantry_item(item)


@router.delete("/{item_id}", status_code=204)
def delete_pantry_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(PantryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Vorratseintrag nicht gefunden")
    db.delete(item)
    db.commit()

    active_plan = db.query(MealPlan).filter(MealPlan.status == "active").first()
    if active_plan:
        rebuild_shopping_list(db, active_plan)


@router.get("/suggestions")
def pantry_recipe_suggestions(db: Session = Depends(get_db)):
    raw = suggest_recipes_from_pantry(db, limit=8)
    return [
        {
            "recipe": serialize_recipe(db, item["recipe"]).model_dump(),
            "matched_ingredients": item["matched_ingredients"],
            "missing_count": item["missing_count"],
            "coverage_pct": item["coverage_pct"],
        }
        for item in raw
    ]
