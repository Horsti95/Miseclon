from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AppSettings, IngredientOfferMatch, MealPlan, PriceOffer, SyncRun
from ..schemas import OfferOut, OfferSyncRequest
from ..services.price_pipeline import sync_weekly_offers
from ..services.shopping import rebuild_shopping_list


router = APIRouter(prefix="/api/offers", tags=["offers"])


@router.get("", response_model=list[OfferOut])
def list_offers(
    store: str | None = Query(default=None),
    matched_only: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    offers = db.query(PriceOffer).order_by(PriceOffer.fetched_at.desc()).limit(250).all()
    matches_by_offer: dict[int, IngredientOfferMatch] = {}
    for m in db.query(IngredientOfferMatch).all():
        prev = matches_by_offer.get(m.offer_id)
        if not prev or m.confidence > prev.confidence:
            matches_by_offer[m.offer_id] = m

    out: list[OfferOut] = []
    for o in offers:
        if store and store.lower() not in o.store_name.lower():
            continue
        m = matches_by_offer.get(o.id)
        if matched_only and (not m or m.is_rejected):
            continue

        prot_per_eur = None
        if m and m.ingredient and not m.is_rejected and o.base_price_eur and o.base_price_eur > 0:
            if o.base_unit == "kg" and m.ingredient.protein_100 > 0:
                # 1 kg has protein_100 * 10 grams of protein
                prot_per_eur = round((m.ingredient.protein_100 * 10.0) / o.base_price_eur, 1)

        out.append(
            OfferOut(
                id=o.id,
                store_name=o.store_name,
                source_provider=o.source_provider,
                raw_title=o.raw_title,
                brand=o.brand,
                price_eur=round(o.price_eur, 2),
                base_price_eur=o.base_price_eur,
                base_unit=o.base_unit,
                pack_size_value=o.pack_size_value,
                pack_size_unit=o.pack_size_unit,
                is_promo=o.is_promo,
                is_organic=o.is_organic,
                valid_from=o.valid_from,
                valid_to=o.valid_to,
                matched_ingredient_id=m.ingredient_id if m else None,
                matched_ingredient_name=m.ingredient.name if (m and m.ingredient) else None,
                match_id=m.id if m else None,
                match_confidence=m.confidence if m else None,
                match_confirmed=m.is_confirmed if m else False,
                match_rejected=m.is_rejected if m else False,
                protein_per_euro=prot_per_eur,
            )
        )
    return out


@router.post("/sync")
def trigger_offer_sync(payload: OfferSyncRequest, db: Session = Depends(get_db)):
    app_settings = db.get(AppSettings, 1)
    postal_code = payload.postal_code or (app_settings.postal_code if app_settings else "50667")
    run = sync_weekly_offers(db, postal_code=postal_code, queries=payload.queries)

    active_plan = db.query(MealPlan).filter(MealPlan.status == "active").first()
    if active_plan and run.matches_created > 0:
        rebuild_shopping_list(db, active_plan)

    return {
        "id": run.id,
        "provider": run.provider,
        "postal_code": run.postal_code,
        "status": run.status,
        "offers_fetched": run.offers_fetched,
        "matches_created": run.matches_created,
        "error_message": run.error_message,
    }


@router.patch("/matches/{match_id}")
def review_offer_match(
    match_id: int,
    action: str = Query(pattern="^(confirm|reject)$"),
    db: Session = Depends(get_db),
):
    m = db.get(IngredientOfferMatch, match_id)
    if not m:
        raise HTTPException(status_code=404, detail="Match nicht gefunden")
    if action == "confirm":
        m.is_confirmed = True
        m.is_rejected = False
        m.confidence = 1.0
    else:
        m.is_rejected = True
        m.is_confirmed = False
    db.commit()

    active_plan = db.query(MealPlan).filter(MealPlan.status == "active").first()
    if active_plan:
        rebuild_shopping_list(db, active_plan)

    return {"id": m.id, "is_confirmed": m.is_confirmed, "is_rejected": m.is_rejected}


@router.get("/sync-runs")
def list_sync_runs(db: Session = Depends(get_db)):
    runs = db.query(SyncRun).order_by(SyncRun.started_at.desc()).limit(15).all()
    return [
        {
            "id": r.id,
            "provider": r.provider,
            "postal_code": r.postal_code,
            "status": r.status,
            "offers_fetched": r.offers_fetched,
            "matches_created": r.matches_created,
            "error_message": r.error_message,
            "started_at": r.started_at.isoformat() if r.started_at else None,
        }
        for r in runs
    ]
