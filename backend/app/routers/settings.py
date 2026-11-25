from __future__ import annotations

import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AppSettings, MealPlan, Store
from ..schemas import SettingsOut, SettingsUpdate
from ..services.shopping import rebuild_shopping_list
from .serializers import serialize_settings


router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    s = db.get(AppSettings, 1)
    if not s:
        s = AppSettings(id=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return serialize_settings(s)


@router.put("", response_model=SettingsOut)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    s = db.get(AppSettings, 1)
    if not s:
        s = AppSettings(id=1)
        db.add(s)

    data = payload.model_dump(exclude_none=True)
    store_pref_changed = "max_stores_per_trip" in data

    if "enabled_stores" in data:
        s.enabled_stores_json = json.dumps(data.pop("enabled_stores"), ensure_ascii=False)
    if "excluded_ingredients" in data:
        s.excluded_ingredients_json = json.dumps(
            data.pop("excluded_ingredients"), ensure_ascii=False
        )
    if "kitchen_equipment" in data:
        s.kitchen_equipment_json = json.dumps(
            data.pop("kitchen_equipment"), ensure_ascii=False
        )

    for k, v in data.items():
        setattr(s, k, v)

    db.commit()
    db.refresh(s)

    if store_pref_changed:
        active_plan = db.query(MealPlan).filter(MealPlan.status == "active").first()
        if active_plan:
            rebuild_shopping_list(db, active_plan)

    return serialize_settings(s)


@router.get("/stores")
def list_stores(db: Session = Depends(get_db)):
    stores = db.query(Store).order_by(Store.priority.asc()).all()
    return [
        {
            "id": st.id,
            "chain": st.chain,
            "display_name": st.display_name,
            "enabled": st.enabled,
            "priority": st.priority,
        }
        for st in stores
    ]
