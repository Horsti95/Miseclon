from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_DIST_DIR, settings
from .database import Base, SessionLocal, engine
from .models import AppSettings, Ingredient, MealPlan, PantryItem
from .routers import ai, ingredients, meal_plans, offers, pantry, recipes, settings as settings_router, shopping
from .schemas import MealPlanGenerateRequest
from .seed_ingredients import seed_stores_and_ingredients
from .seed_recipes import seed_recipes
from .services.planner import generate_meal_plan


def _run_lightweight_migrations() -> None:
    """Safely add newly introduced columns on existing local SQLite databases."""
    with engine.begin() as conn:
        cols = [
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(app_settings)").fetchall()
        ]
        if cols and "kitchen_equipment_json" not in cols:
            conn.exec_driver_sql(
                """ALTER TABLE app_settings ADD COLUMN kitchen_equipment_json TEXT DEFAULT '["airfryer", "stove_2_burners", "oven"]'"""
            )


def bootstrap_database() -> None:
    """Create tables and idempotently seed ALDI fundamentals, 52+ recipes, and starter plan."""
    Base.metadata.create_all(bind=engine)
    _run_lightweight_migrations()
    db = SessionLocal()
    try:
        app_settings = db.get(AppSettings, 1)
        if not app_settings:
            app_settings = AppSettings(id=1)
            db.add(app_settings)
            db.commit()

        slug_map = seed_stores_and_ingredients(db)
        seed_recipes(db, slug_map)

        # Seed minimal everyday staples in pantry only on brand-new database
        if db.query(PantryItem).count() == 0 and db.query(MealPlan).count() == 0:
            starter_pantry = [
                ("salz-pfeffer", 400.0, "pantry", 730),
                ("olivenoel", 500.0, "pantry", 240),
                ("rapsoel", 750.0, "pantry", 240),
                ("paprikapulver", 60.0, "pantry", 365),
                ("zimt", 40.0, "pantry", 365),
                ("kreuzkuemmel", 40.0, "pantry", 365),
                ("italienische-kraeuter", 35.0, "pantry", 365),
                ("gemuesebruehe", 150.0, "pantry", 365),
                ("knoblauch", 10.0, "pantry", 30),
                ("haferflocken", 350.0, "pantry", 120),
            ]
            for slug, qty, loc, days in starter_pantry:
                ing: Ingredient | None = slug_map.get(slug)
                if ing:
                    db.add(
                        PantryItem(
                            ingredient_id=ing.id,
                            quantity=qty,
                            unit=ing.default_unit,
                            location=loc,
                            expires_at=(date.today() + timedelta(days=days)).isoformat(),
                            use_priority="normal",
                            notes="Standard-Grundvorrat",
                        )
                    )
            db.commit()

        if db.query(MealPlan).count() == 0:
            generate_meal_plan(
                db,
                MealPlanGenerateRequest(
                    days_count=7,
                    servings_per_meal=app_settings.default_servings,
                    max_effort_level=app_settings.default_max_effort,
                    target_budget_eur=app_settings.weekly_budget_eur,
                    active_slots=["breakfast", "lunch", "dinner", "snack"],
                    batch_cooking=True,
                    use_ai=False,
                ),
            )
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    bootstrap_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Lokaler Meal-Planner & ALDI-Einkaufs-Assistent (inspiriert von Mise)",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(settings_router.router)
app.include_router(ingredients.router)
app.include_router(pantry.router)
app.include_router(recipes.router)
app.include_router(meal_plans.router)
app.include_router(shopping.router)
app.include_router(offers.router)
app.include_router(ai.router)


@app.get("/api/health")
def api_health():
    return {"status": "ok", "app": settings.app_name}


# Serve built React SPA if present
if FRONTEND_DIST_DIR.exists():
    assets_dir = FRONTEND_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        candidate = FRONTEND_DIST_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(FRONTEND_DIST_DIR / "index.html"))
else:
    @app.get("/")
    def root_dev_hint():
        return {
            "app": settings.app_name,
            "message": "Backend läuft! Frontend bitte mit 'npm run build' in frontend/ bauen oder Vite Dev-Server nutzen.",
            "docs": "/docs",
        }
