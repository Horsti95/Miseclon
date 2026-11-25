from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AppSettings, LlmGenerationLog
from ..schemas import AiRecipeRequest, RecipeOut
from ..services.llm_client import LocalLlmClient
from ..services.planner import generate_recipe_with_ai
from .serializers import serialize_recipe


router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/health")
def llm_health(db: Session = Depends(get_db)):
    app_settings = db.get(AppSettings, 1)
    if not app_settings:
        app_settings = AppSettings(id=1)
        db.add(app_settings)
        db.commit()
    client = LocalLlmClient(app_settings)
    return client.check_health()


@router.post("/generate-recipe", response_model=RecipeOut, status_code=201)
def ai_create_recipe(payload: AiRecipeRequest, db: Session = Depends(get_db)):
    try:
        recipe = generate_recipe_with_ai(
            db=db,
            prompt=payload.prompt,
            effort_level=payload.effort_level,
            servings=payload.servings,
            meal_type=payload.meal_type,
            use_pantry=payload.use_pantry,
        )
        return serialize_recipe(db, recipe)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )


@router.get("/logs")
def llm_logs(db: Session = Depends(get_db)):
    logs = (
        db.query(LlmGenerationLog)
        .order_by(LlmGenerationLog.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": l.id,
            "task_type": l.task_type,
            "model": l.model,
            "status": l.status,
            "duration_ms": l.duration_ms,
            "retries": l.retries,
            "error_message": l.error_message,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]
