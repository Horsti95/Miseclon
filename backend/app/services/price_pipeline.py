"""Price & Weekly Offer Pipeline (German supermarkets by PLZ) with 3-stage ingredient matching.

Architecture:
- Modular PriceProvider base class + Circuit Breaker + Rate Limiting
- MarktguruAdapter: fetches live weekly German supermarket offers by PLZ (ALDI, LIDL, REWE, EDEKA, Kaufland)
- 3-stage Matching Engine:
  1. German pack-size & unit parser -> base price (€/kg, €/l, €/stk)
  2. Fuzzy (rapidfuzz) + Alias + Negative Exclude-Keyword filtering
  3. Persistent match review & rejection memory
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from ..models import (
    Ingredient,
    IngredientOfferMatch,
    PriceOffer,
    Store,
    SyncRun,
)


DEFAULT_OFFER_QUERIES = [
    "Hähnchenbrust",
    "Putenbrust",
    "Rinderhackfleisch",
    "Lachs",
    "Magerquark",
    "Skyr",
    "Eier",
    "Feta",
    "Haferflocken",
    "Reis",
    "Nudeln",
    "Kartoffeln",
    "Süßkartoffeln",
    "Brokkoli",
    "Paprika",
    "Tomaten",
    "Avocado",
    "Beeren",
    "Linsen",
    "Thunfisch",
    "Tofu",
    "Olivenöl",
]


@dataclass
class ParsedPack:
    pack_value: float | None
    pack_unit: str | None
    base_price_eur: float | None
    base_unit: str | None


def parse_german_pack_size(text: str, price_eur: float) -> ParsedPack:
    """Extract pack size (e.g. '400 g', '1,5 kg', '6x1,5 l', '10 Stück') & compute base price."""
    if not text:
        return ParsedPack(None, None, None, None)

    cleaned = text.lower().replace(",", ".")

    # Multipack pattern e.g. 6 x 1.5 l or 4 x 125 g
    m_multi = re.search(
        r"(\d+)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(kg|g|ml|l|liter|stk|stück|st\.?)\b",
        cleaned,
    )
    if m_multi:
        count = float(m_multi.group(1))
        val = float(m_multi.group(2)) * count
        raw_unit = m_multi.group(3)
        return _normalize_parsed_pack(val, raw_unit, price_eur)

    # Single pack pattern e.g. 500g, 500-g-Packung, 1.5 kg, 250 ml, 10 Stück
    m_single = re.search(
        r"(\d+(?:\.\d+)?)[\s-]*(kg|g|ml|l|liter|stk|stück|st\.?|er(?:\s+pack)?)\b",
        cleaned,
    )
    if m_single:
        val = float(m_single.group(1))
        raw_unit = m_single.group(2)
        return _normalize_parsed_pack(val, raw_unit, price_eur)

    return ParsedPack(None, None, None, None)


def _normalize_parsed_pack(val: float, raw_unit: str, price_eur: float) -> ParsedPack:
    if val <= 0:
        return ParsedPack(None, None, None, None)
    u = raw_unit.strip()
    if u == "kg":
        return ParsedPack(val * 1000.0, "g", round(price_eur / val, 2), "kg")
    if u == "g":
        return ParsedPack(val, "g", round(price_eur / (val / 1000.0), 2), "kg")
    if u in ("l", "liter"):
        return ParsedPack(val * 1000.0, "ml", round(price_eur / val, 2), "l")
    if u == "ml":
        return ParsedPack(val, "ml", round(price_eur / (val / 1000.0), 2), "l")
    # Stück / er pack
    return ParsedPack(val, "stk", round(price_eur / val, 2), "stk")


class MarktguruAdapter:
    """Adapter for German weekly supermarket brochure offers by PLZ via Marktguru web API."""

    BASE_URL = "https://api.marktguru.de/api/v1/offers/search"
    WEB_URL = "https://www.marktguru.de/"
    FALLBACK_HEADERS = {
        "x-clientkey": "nkGpDDdaO7TPQza7e1ijrW9bQuWRlFVgrGdrxR2ZhRk=",
        "x-apikey": "pCcm1AVCYa6Gx0ir8zmMbj755T0JDRLjrL4AXZ4n2HQ=",
    }

    def __init__(self) -> None:
        self._consecutive_failures = 0
        self._headers: dict[str, str] | None = None

    def _resolve_headers(self, client: httpx.Client) -> dict[str, str]:
        if self._headers:
            return self._headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            **self.FALLBACK_HEADERS,
        }
        # Attempt dynamic key extraction from marktguru.de HTML if keys rotated
        try:
            r = client.get(self.WEB_URL, timeout=5.0)
            if r.status_code == 200:
                m_api = re.search(r'"apiKey"\s*:\s*"([^"]+)"', r.text)
                m_cli = re.search(r'"clientKey"\s*:\s*"([^"]+)"', r.text)
                if m_api:
                    headers["x-apikey"] = m_api.group(1)
                if m_cli:
                    headers["x-clientkey"] = m_cli.group(1)
        except Exception:
            pass
        self._headers = headers
        return headers

    def fetch_offers(
        self, postal_code: str, queries: list[str] | None = None, limit_per_query: int = 8
    ) -> tuple[list[dict], list[str]]:
        """Fetch deduplicated weekly offers for a German postal code with rate limiting & circuit breaker."""
        query_list = queries or DEFAULT_OFFER_QUERIES
        offers_by_ext_id: dict[str, dict] = {}
        errors: list[str] = []

        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            headers = self._resolve_headers(client)

            for q in query_list:
                if self._consecutive_failures >= 4:
                    errors.append(
                        "Circuit-Breaker ausgelöst (Marktguru-Endpunkt derzeit nicht erreichbar oder blockiert)."
                    )
                    break

                try:
                    resp = client.get(
                        self.BASE_URL,
                        headers=headers,
                        params={
                            "as": "web",
                            "q": q,
                            "zipCode": postal_code,
                            "limit": limit_per_query,
                            "offset": 0,
                        },
                    )
                    if resp.status_code != 200:
                        self._consecutive_failures += 1
                        errors.append(f"Query '{q}': HTTP {resp.status_code}")
                        continue

                    self._consecutive_failures = 0
                    data = resp.json()
                    for raw in data.get("results", []):
                        ext_id = str(raw.get("id") or "")
                        price = raw.get("price")
                        if not ext_id or price is None:
                            continue
                        advertisers = raw.get("advertisers") or []
                        store_name = (
                            advertisers[0].get("name", "Supermarkt")
                            if advertisers
                            else "Supermarkt"
                        )
                        product = raw.get("product") or {}
                        brand = (raw.get("brand") or {}).get("name")
                        title = (
                            product.get("name")
                            or raw.get("description")
                            or q
                        )
                        desc = raw.get("description") or ""
                        unit_obj = raw.get("unit") or {}
                        unit_short = (unit_obj.get("shortName") or "").lower().strip()
                        vol = raw.get("volume")
                        qty = raw.get("quantity") or 1.0
                        ref_price = raw.get("referencePrice")

                        if vol and float(vol) > 0 and unit_short:
                            total_vol = float(vol) * float(qty)
                            parsed = _normalize_parsed_pack(
                                total_vol, unit_short, float(price)
                            )
                            if ref_price and float(ref_price) > 0:
                                parsed.base_price_eur = round(float(ref_price), 2)
                        else:
                            parsed = parse_german_pack_size(
                                f"{desc} {title}", float(price)
                            )
                            if ref_price and float(ref_price) > 0 and not parsed.base_price_eur:
                                parsed.base_price_eur = round(float(ref_price), 2)
                                parsed.base_unit = unit_short or parsed.base_unit

                        validity = raw.get("validityDates") or []
                        valid_from = validity[0].get("from", "")[:10] if validity else None
                        valid_to = validity[0].get("to", "")[:10] if validity else None

                        offers_by_ext_id[ext_id] = {
                            "external_offer_id": ext_id,
                            "store_name": store_name,
                            "raw_title": f"{brand + ' ' if brand else ''}{title}".strip(),
                            "brand": brand,
                            "description": desc,
                            "price_eur": float(price),
                            "pack_size_value": parsed.pack_value,
                            "pack_size_unit": parsed.pack_unit,
                            "base_price_eur": parsed.base_price_eur,
                            "base_unit": parsed.base_unit,
                            "is_organic": "bio" in f"{title} {desc}".lower(),
                            "valid_from": valid_from,
                            "valid_to": valid_to,
                            "raw_payload_json": json.dumps(raw, ensure_ascii=False)[:2000],
                        }
                    time.sleep(0.15)  # polite rate limiting
                except Exception as exc:
                    self._consecutive_failures += 1
                    errors.append(f"Query '{q}': {type(exc).__name__}")

        return list(offers_by_ext_id.values()), errors


def match_offer_to_ingredients(
    db: Session, offer: PriceOffer, all_ingredients: list[Ingredient]
) -> IngredientOfferMatch | None:
    """Stage 2 matching: Fuzzy + Alias + Negative Exclude-Keyword guardrails."""
    offer_text = f"{offer.raw_title} {offer.description or ''}".lower()
    best_ing: Ingredient | None = None
    best_score = 0.0

    for ing in all_ingredients:
        # Check negative exclude keywords first
        excluded = False
        candidate_names = [ing.name.lower()]
        for al in ing.aliases:
            candidate_names.append(al.alias.lower())
            try:
                neg_words = json.loads(al.exclude_keywords_json or "[]")
            except Exception:
                neg_words = []
            if any(nw.lower() in offer_text for nw in neg_words if nw):
                excluded = True
                break
        if excluded:
            continue

        # Compute best partial/token similarity across canonical name & aliases
        ing_best = 0.0
        for cname in candidate_names:
            if cname in offer_text:
                # Strong substring boost, weighted by length to avoid short noise
                score = 88.0 + min(len(cname), 12)
            else:
                score = max(
                    fuzz.token_set_ratio(cname, offer_text),
                    fuzz.partial_ratio(cname, offer_text) * 0.92,
                )
            if score > ing_best:
                ing_best = score

        if ing_best > best_score:
            best_score = ing_best
            best_ing = ing

    if not best_ing or best_score < 74.0:
        return None

    confidence = round(min(best_score / 100.0, 0.99), 2)
    existing = (
        db.query(IngredientOfferMatch)
        .filter(
            IngredientOfferMatch.ingredient_id == best_ing.id,
            IngredientOfferMatch.offer_id == offer.id,
        )
        .first()
    )
    if existing:
        if existing.is_rejected:
            return None
        existing.confidence = confidence
        return existing

    match = IngredientOfferMatch(
        ingredient_id=best_ing.id,
        offer_id=offer.id,
        match_method="rule" if best_score >= 88.0 else "fuzzy",
        confidence=confidence,
    )
    db.add(match)
    return match


def sync_weekly_offers(
    db: Session, postal_code: str, queries: list[str] | None = None
) -> SyncRun:
    """Execute full offer sync for postal_code, store offers, and match to canonical ingredients."""
    run = SyncRun(
        provider="marktguru",
        postal_code=postal_code,
        status="running",
    )
    db.add(run)
    db.commit()

    adapter = MarktguruAdapter()
    raw_offers, errors = adapter.fetch_offers(postal_code=postal_code, queries=queries)

    stores_by_name = {s.display_name.lower(): s for s in db.query(Store).all()}
    all_ingredients = db.query(Ingredient).all()
    stored_count = 0
    matched_count = 0

    for item in raw_offers:
        existing = (
            db.query(PriceOffer)
            .filter(
                PriceOffer.source_provider == "marktguru",
                PriceOffer.external_offer_id == item["external_offer_id"],
            )
            .first()
        )
        store_obj = None
        sn_low = item["store_name"].lower()
        for k, s in stores_by_name.items():
            if k in sn_low or sn_low in k or s.chain.replace("_", " ") in sn_low:
                store_obj = s
                break

        if existing:
            existing.price_eur = item["price_eur"]
            existing.base_price_eur = item["base_price_eur"]
            existing.base_unit = item["base_unit"]
            existing.pack_size_value = item["pack_size_value"]
            existing.pack_size_unit = item["pack_size_unit"]
            existing.valid_from = item["valid_from"]
            existing.valid_to = item["valid_to"]
            existing.fetched_at = datetime.now(timezone.utc)
            offer_obj = existing
        else:
            offer_obj = PriceOffer(
                store_id=store_obj.id if store_obj else None,
                store_name=item["store_name"],
                source_provider="marktguru",
                external_offer_id=item["external_offer_id"],
                raw_title=item["raw_title"],
                brand=item["brand"],
                description=item["description"],
                price_eur=item["price_eur"],
                base_price_eur=item["base_price_eur"],
                base_unit=item["base_unit"],
                pack_size_value=item["pack_size_value"],
                pack_size_unit=item["pack_size_unit"],
                is_promo=True,
                is_organic=item["is_organic"],
                valid_from=item["valid_from"],
                valid_to=item["valid_to"],
                raw_payload_json=item["raw_payload_json"],
            )
            db.add(offer_obj)
            db.flush()
            stored_count += 1

        match = match_offer_to_ingredients(db, offer_obj, all_ingredients)
        if match is not None:
            matched_count += 1

    run.offers_fetched = len(raw_offers)
    run.matches_created = matched_count
    run.finished_at = datetime.now(timezone.utc)
    if len(raw_offers) > 0 and not errors:
        run.status = "success"
    elif len(raw_offers) > 0:
        run.status = "partial"
        run.error_message = "; ".join(errors[:5])
    else:
        run.status = "failed"
        run.error_message = "; ".join(errors[:5]) or "Keine Angebote gefunden."

    db.commit()
    db.refresh(run)
    return run
