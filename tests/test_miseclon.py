from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.database import SessionLocal
from backend.app.main import app, bootstrap_database
from backend.app.models import Ingredient, PriceOffer
from backend.app.services.price_pipeline import (
    match_offer_to_ingredients,
    parse_german_pack_size,
)


bootstrap_database()
client = TestClient(app)


def test_health_and_spa_root():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    home = client.get("/")
    assert home.status_code == 200
    assert "Miseclon" in home.text


def test_seeded_ingredients_and_recipes_have_accurate_macros():
    ings = client.get("/api/ingredients").json()
    assert len(ings) >= 100
    hafer = next(i for i in ings if i["slug"] == "haferflocken")
    assert hafer["carb_type"] == "complex"
    assert hafer["reference_store"] == "ALDI"
    assert hafer["reference_price_eur"] > 0

    recipes = client.get("/api/recipes").json()
    assert len(recipes) >= 40
    for r in recipes:
        assert r["kcal_per_serving"] > 50
        assert r["protein_g"] >= 3
        assert len(r["instructions"]) >= 2
        assert r["effort_level"] in (1, 2, 3)


def test_generate_plan_respects_effort_servings_and_days():
    resp = client.post(
        "/api/meal-plans/generate",
        json={
            "days_count": 5,
            "servings_per_meal": 3,
            "max_effort_level": 1,
            "target_budget_eur": 80.0,
            "active_slots": ["breakfast", "lunch", "dinner"],
            "batch_cooking": True,
            "use_ai": False,
        },
    )
    assert resp.status_code == 200
    plan = resp.json()
    assert plan["days_count"] == 5
    assert plan["servings_per_meal"] == 3
    assert plan["max_effort_level"] == 1
    assert len(plan["entries"]) == 15
    for entry in plan["entries"]:
        assert entry["servings"] == 3
        assert entry["recipe"]["effort_level"] == 1

    # Scale people count from 3 -> 1 and confirm shopping list shrinks
    sl_before = client.get("/api/shopping-list/active").json()
    scaled = client.patch(f"/api/meal-plans/{plan['id']}/servings?servings=1").json()
    assert scaled["servings_per_meal"] == 1
    sl_after = client.get("/api/shopping-list/active").json()
    assert sl_after["total_estimated_eur"] < sl_before["total_estimated_eur"]


def test_shopping_list_manual_item_and_actual_price():
    sl = client.get("/api/shopping-list/active").json()
    assert sl["total_items_count"] > 0

    first_item = sl["items"][0]
    updated = client.patch(
        f"/api/shopping-list/items/{first_item['id']}",
        json={"is_checked": True, "actual_price_eur": 1.23},
    ).json()
    patched_item = next(i for i in updated["items"] if i["id"] == first_item["id"])
    assert patched_item["is_checked"] is True
    assert patched_item["actual_price_eur"] == 1.23
    assert patched_item["price_confidence"] == "verified"

    added = client.post(
        "/api/shopping-list/items",
        json={
            "custom_name": "Küchenrolle Test",
            "category": "Sonstiges",
            "to_buy_amount": 1,
            "unit": "stk",
            "estimated_price_eur": 2.49,
        },
    )
    assert added.status_code == 201
    manual = next(i for i in added.json()["items"] if i["custom_name"] == "Küchenrolle Test")
    deleted = client.delete(f"/api/shopping-list/items/{manual['id']}")
    assert deleted.status_code == 200


def test_pantry_deduction_and_suggestions():
    ings = client.get("/api/ingredients").json()
    skyr = next(i for i in ings if i["slug"] == "skyr")
    created = client.post(
        "/api/pantry",
        json={
            "ingredient_id": skyr["id"],
            "quantity": 1000,
            "unit": "g",
            "location": "fridge",
            "use_priority": "urgent",
        },
    )
    assert created.status_code == 201
    item_id = created.json()["id"]

    suggestions = client.get("/api/pantry/suggestions").json()
    assert len(suggestions) > 0

    del_resp = client.delete(f"/api/pantry/{item_id}")
    assert del_resp.status_code == 204


def test_kitchen_equipment_and_airfryer_recipes():
    s = client.get("/api/settings").json()
    eq = s["kitchen_equipment"]
    assert "airfryer" in eq
    assert "stove_2_burners" in eq
    assert "oven" in eq
    assert "microwave" not in eq

    recipes = client.get("/api/recipes").json()
    airfryer_recipes = [r for r in recipes if "airfryer" in r["tags"]]
    assert len(airfryer_recipes) >= 10
    for r in recipes:
        joined = " ".join(r["instructions"]).lower()
        assert "mikrowelle" not in joined, f"Unexpected microwave instruction in {r['title']}"


def test_pack_size_parser_and_negative_keyword_guardrails():
    p1 = parse_german_pack_size("Wiesenhof Hähnchenbrust 400 g Packung", 4.49)
    assert p1.pack_value == 400.0
    assert p1.pack_unit == "g"
    assert p1.base_unit == "kg"
    assert abs((p1.base_price_eur or 0) - 11.23) < 0.05

    p2 = parse_german_pack_size("Mineralwasser 6 x 1,5 L", 2.70)
    assert p2.pack_value == 9000.0
    assert p2.base_unit == "l"
    assert abs((p2.base_price_eur or 0) - 0.30) < 0.02

    p3 = parse_german_pack_size("Freilandeier 10 Stück", 2.29)
    assert p3.pack_value == 10.0
    assert p3.base_unit == "stk"

    # Negative keyword guardrails: Haferdrink must NOT match Haferflocken!
    db = SessionLocal()
    try:
        all_ings = db.query(Ingredient).all()
        hafer = next(i for i in all_ings if i.slug == "haferflocken")
        fake_offer = PriceOffer(
            store_name="ALDI",
            source_provider="test",
            external_offer_id="test-neg-1",
            raw_title="Oatly Barista Haferdrink 1L",
            price_eur=1.79,
        )
        db.add(fake_offer)
        db.flush()
        match = match_offer_to_ingredients(db, fake_offer, all_ings)
        assert match is None or match.ingredient_id != hafer.id
        db.rollback()
    finally:
        db.close()
