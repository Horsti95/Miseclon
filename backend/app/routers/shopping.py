from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import MealPlan, ShoppingList, ShoppingListItem
from ..schemas import ShoppingItemManualCreate, ShoppingItemUpdate, ShoppingListOut
from ..services.shopping import (
    move_checked_items_to_pantry,
    rebuild_shopping_list,
    record_actual_price_to_history,
)
from .serializers import serialize_shopping_list


router = APIRouter(prefix="/api/shopping-list", tags=["shopping-list"])


def _get_active_plan_and_list(db: Session) -> tuple[MealPlan, ShoppingList]:
    plan = (
        db.query(MealPlan)
        .filter(MealPlan.status == "active")
        .order_by(MealPlan.id.desc())
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Kein aktiver Wochenplan vorhanden")
    sl = db.query(ShoppingList).filter(ShoppingList.meal_plan_id == plan.id).first()
    if not sl:
        sl = rebuild_shopping_list(db, plan)
    return plan, sl


@router.get("/active", response_model=ShoppingListOut)
def get_active_shopping_list(db: Session = Depends(get_db)):
    plan, sl = _get_active_plan_and_list(db)
    return serialize_shopping_list(db, sl, plan)


@router.post("/rebuild", response_model=ShoppingListOut)
def force_rebuild_shopping_list(db: Session = Depends(get_db)):
    plan, _ = _get_active_plan_and_list(db)
    sl = rebuild_shopping_list(db, plan)
    return serialize_shopping_list(db, sl, plan)


@router.patch("/items/{item_id}", response_model=ShoppingListOut)
def update_shopping_item(
    item_id: int, payload: ShoppingItemUpdate, db: Session = Depends(get_db)
):
    item = db.get(ShoppingListItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Einkaufseintrag nicht gefunden")

    if payload.is_checked is not None:
        item.is_checked = payload.is_checked
    if payload.to_buy_amount is not None:
        item.to_buy_amount = payload.to_buy_amount
    if payload.actual_price_eur is not None:
        item.actual_price_eur = payload.actual_price_eur
        item.price_confidence = "verified"
        record_actual_price_to_history(db, item)

    db.commit()
    plan, sl = _get_active_plan_and_list(db)
    db.refresh(sl)
    return serialize_shopping_list(db, sl, plan)


@router.post("/items", response_model=ShoppingListOut, status_code=201)
def add_manual_shopping_item(
    payload: ShoppingItemManualCreate, db: Session = Depends(get_db)
):
    plan, sl = _get_active_plan_and_list(db)
    db.add(
        ShoppingListItem(
            shopping_list_id=sl.id,
            ingredient_id=None,
            custom_name=payload.custom_name.strip(),
            category=payload.category,
            needed_amount=payload.to_buy_amount,
            pantry_deducted_amount=0.0,
            to_buy_amount=payload.to_buy_amount,
            unit=payload.unit,
            pack_size=payload.to_buy_amount,
            suggested_pack_count=1,
            remainder_amount=0.0,
            assigned_store_name=payload.assigned_store_name,
            estimated_price_eur=payload.estimated_price_eur,
            price_confidence="estimated",
            is_checked=False,
            manual_addition=True,
        )
    )
    db.commit()
    db.refresh(sl)
    return serialize_shopping_list(db, sl, plan)


@router.delete("/items/{item_id}", response_model=ShoppingListOut)
def delete_shopping_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(ShoppingListItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Einkaufseintrag nicht gefunden")
    db.delete(item)
    db.commit()
    plan, sl = _get_active_plan_and_list(db)
    db.refresh(sl)
    return serialize_shopping_list(db, sl, plan)


@router.post("/move-to-pantry")
def move_checked_to_pantry(db: Session = Depends(get_db)):
    plan, sl = _get_active_plan_and_list(db)
    moved = move_checked_items_to_pantry(db, sl)
    db.refresh(sl)
    return {
        "moved_count": moved,
        "shopping_list": serialize_shopping_list(db, sl, plan).model_dump(),
    }
