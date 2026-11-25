"""Single-URL Recipe Importer (schema.org/Recipe JSON-LD) & OpenFoodFacts lookup.

Allows the user to import any individual recipe URL (e.g. Chefkoch, EatSmarter, REWE,
Kitchen Stories) cleanly with automatic German ingredient parsing, canonical matching,
and deterministic macro + ALDI cost calculation.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup
from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session

from ..models import Ingredient, Recipe, RecipeIngredient
from .nutrition import recalculate_recipe_metrics


def _parse_iso_duration_minutes(val: str | None) -> int:
    if not val or not isinstance(val, str):
        return 0
    hours = 0
    mins = 0
    m_h = re.search(r"(\d+)H", val)
    m_m = re.search(r"(\d+)M", val)
    if m_h:
        hours = int(m_h.group(1))
    if m_m:
        mins = int(m_m.group(1))
    return hours * 60 + mins


def _extract_recipe_ld_json(html: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        raw = script.string or script.get_text() or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        candidates: list[dict] = []
        if isinstance(data, list):
            candidates.extend(x for x in data if isinstance(x, dict))
        elif isinstance(data, dict):
            if "@graph" in data and isinstance(data["@graph"], list):
                candidates.extend(x for x in data["@graph"] if isinstance(x, dict))
            candidates.append(data)

        for obj in candidates:
            t = obj.get("@type")
            if t == "Recipe" or (isinstance(t, list) and "Recipe" in t):
                return obj
    return None


def _extract_instructions(raw_instructions: Any) -> list[str]:
    steps: list[str] = []
    if isinstance(raw_instructions, str):
        parts = [p.strip() for p in re.split(r"\n+|\.\s+(?=[A-ZÄÖÜ])", raw_instructions) if p.strip()]
        return parts or [raw_instructions.strip()]
    if isinstance(raw_instructions, list):
        for item in raw_instructions:
            if isinstance(item, str) and item.strip():
                steps.append(item.strip())
            elif isinstance(item, dict):
                if item.get("text"):
                    steps.append(str(item["text"]).strip())
                elif isinstance(item.get("itemListElement"), list):
                    steps.extend(_extract_instructions(item["itemListElement"]))
    return steps


def _parse_german_ingredient_line(line: str) -> tuple[float, str, str]:
    """Parse lines like '250 g Haferflocken', '2 EL Olivenöl', '3 Eier', '1 Dose Kichererbsen'."""
    text = line.strip()
    text = text.replace("½", "0.5").replace("¼", "0.25").replace("¾", "0.75")

    m = re.match(
        r"^(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l|el|tl|stk|stück|st\.?|dose|dosen|becher|packung|pck\.?|bund|zehe|zehen|scheibe|scheiben)?\s*(.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not m:
        return 100.0, "g", text

    amount = float(m.group(1).replace(",", "."))
    raw_unit = (m.group(2) or "").lower().strip(".")
    name = m.group(3).strip(" ,;-")

    if raw_unit == "kg":
        return amount * 1000.0, "g", name
    if raw_unit == "g":
        return amount, "g", name
    if raw_unit == "l":
        return amount * 1000.0, "ml", name
    if raw_unit == "ml":
        return amount, "ml", name
    if raw_unit == "el":
        return amount * 15.0, "ml" if "öl" in name.lower() or "sauce" in name.lower() else "g", name
    if raw_unit == "tl":
        return amount * 5.0, "g", name
    if raw_unit in ("dose", "dosen"):
        return amount * 265.0, "g", name
    if raw_unit in ("becher", "packung", "pck"):
        return amount * 200.0, "g", name
    if raw_unit in ("stk", "stück", "st", "zehe", "zehen", "scheibe", "scheiben", ""):
        return amount, "stk", name
    if raw_unit == "bund":
        return amount * 30.0, "g", name
    return amount, "g", name


def import_recipe_from_url(db: Session, url: str) -> Recipe:
    """Fetch a single recipe URL, parse schema.org/Recipe JSON-LD, and store with calculated macros."""
    if not url.startswith(("http://", "https://")):
        raise ValueError("Bitte eine gültige http:// oder https:// URL angeben.")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept-Language": "de-DE,de;q=0.9",
    }
    with httpx.Client(timeout=12.0, follow_redirects=True) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        html = resp.text

    ld = _extract_recipe_ld_json(html)
    if not ld:
        raise ValueError(
            "Auf dieser Seite wurden keine strukturierten Rezeptdaten (schema.org/Recipe) gefunden."
        )

    title = str(ld.get("name") or "Importiertes Rezept").strip()[:190]
    description = str(ld.get("description") or "").strip()[:450]

    raw_yield = ld.get("recipeYield")
    servings = 2
    if isinstance(raw_yield, list) and raw_yield:
        raw_yield = raw_yield[0]
    if isinstance(raw_yield, (int, float)):
        servings = max(1, min(int(raw_yield), 12))
    elif isinstance(raw_yield, str):
        m_y = re.search(r"(\d+)", raw_yield)
        if m_y:
            servings = max(1, min(int(m_y.group(1)), 12))

    prep_min = _parse_iso_duration_minutes(ld.get("prepTime")) or 10
    cook_min = _parse_iso_duration_minutes(ld.get("cookTime"))
    total_min = _parse_iso_duration_minutes(ld.get("totalTime"))
    if not cook_min and total_min > prep_min:
        cook_min = total_min - prep_min

    total_time = prep_min + cook_min
    effort_level = 1 if total_time <= 18 else (2 if total_time <= 35 else 3)

    instructions = _extract_instructions(ld.get("recipeInstructions"))
    if not instructions:
        instructions = ["Zutaten wie angegeben vorbereiten und gar kochen."]

    raw_ingredients = ld.get("recipeIngredient") or []
    if not isinstance(raw_ingredients, list) or not raw_ingredients:
        raise ValueError("Das Rezept enthält keine lesbare Zutatenliste.")

    # Prepare lookup across canonical ingredients & aliases
    all_ingredients = db.query(Ingredient).all()
    search_pool: dict[str, Ingredient] = {}
    for ing in all_ingredients:
        search_pool[ing.name.lower()] = ing
        for al in ing.aliases:
            search_pool[al.alias.lower()] = ing
    pool_keys = list(search_pool.keys())

    recipe = Recipe(
        title=title,
        description=description or f"Importiert von {url}",
        servings=servings,
        prep_time_min=prep_min,
        cook_time_min=cook_min,
        effort_level=effort_level,
        diet_type="omnivore",
        meal_types_json=json.dumps(["lunch", "dinner"]),
        tags_json=json.dumps(["importiert"]),
        instructions_json=json.dumps(instructions, ensure_ascii=False),
        source="url_import",
        source_url=url,
        image_emoji="🔗",
    )
    db.add(recipe)
    db.flush()

    for idx, line in enumerate(raw_ingredients):
        if not isinstance(line, str) or not line.strip():
            continue
        amount, unit, parsed_name = _parse_german_ingredient_line(line)
        clean_name = re.sub(r"\([^)]*\)", "", parsed_name).strip()

        matched = search_pool.get(clean_name.lower())
        if not matched and pool_keys:
            best = process.extractOne(clean_name.lower(), pool_keys, scorer=fuzz.WRatio)
            if best and best[1] >= 74:
                matched = search_pool[best[0]]

        if not matched:
            # Create lightweight fallback ingredient so user never loses an imported item
            slug = f"import-{abs(hash(clean_name.lower())) % 1000000}"
            matched = db.query(Ingredient).filter(Ingredient.slug == slug).first()
            if not matched:
                matched = Ingredient(
                    slug=slug,
                    name=clean_name[:120] or parsed_name[:120],
                    category="Sonstiges",
                    default_unit=unit if unit in ("g", "ml", "stk") else "g",
                    grams_per_unit=100.0 if unit == "stk" else 1.0,
                    kcal_100=120.0,
                    protein_100=5.0,
                    carbs_100=15.0,
                    sugar_100=3.0,
                    fiber_100=2.0,
                    fat_100=4.0,
                    carb_type="mixed",
                    default_pack_size=500.0 if unit != "stk" else 4.0,
                    reference_price_eur=1.99,
                    reference_price_per_base_unit=3.98,
                    reference_store="ALDI",
                    nutrition_source="import_estimate",
                )
                db.add(matched)
                db.flush()

        # Align unit sensibly if matched ingredient uses g/ml while parsed line had stk without grams_per_unit
        final_unit = unit
        final_amount = amount
        if unit == "stk" and matched.default_unit == "g" and matched.grams_per_unit == 1.0:
            final_unit = "g"
            final_amount = round(amount * 100.0, 1)

        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=matched.id,
            amount=final_amount,
            unit=final_unit,
            preparation_note=line.strip()[:115],
            display_order=idx,
        )
        ri.ingredient = matched
        db.add(ri)
        recipe.ingredients.append(ri)

    recalculate_recipe_metrics(db, recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


def search_openfoodfacts(query: str, limit: int = 8) -> list[dict]:
    """Search official OpenFoodFacts Germany API for nutrition & pack sizes."""
    url = "https://de.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": limit,
        "fields": "product_name,brands,quantity,nutriments,code",
    }
    with httpx.Client(timeout=8.0) as client:
        resp = client.get(url, params=params, headers={"User-Agent": "Miseclon/1.0"})
        resp.raise_for_status()
        data = resp.json()

    results = []
    for p in data.get("products", []):
        name = (p.get("product_name") or "").strip()
        if not name:
            continue
        nutr = p.get("nutriments") or {}
        results.append(
            {
                "code": p.get("code"),
                "name": name,
                "brand": p.get("brands") or "",
                "quantity": p.get("quantity") or "",
                "kcal_100": round(float(nutr.get("energy-kcal_100g") or 0), 1),
                "protein_100": round(float(nutr.get("proteins_100g") or 0), 1),
                "carbs_100": round(float(nutr.get("carbohydrates_100g") or 0), 1),
                "sugar_100": round(float(nutr.get("sugars_100g") or 0), 1),
                "fiber_100": round(float(nutr.get("fiber_100g") or 0), 1),
                "fat_100": round(float(nutr.get("fat_100g") or 0), 1),
            }
        )
    return results
