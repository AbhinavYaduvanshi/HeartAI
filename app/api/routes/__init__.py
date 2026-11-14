"""HeartAI API Routes Package."""

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.model_info import router as model_info_router
from app.api.routes.predict import router as predict_router

__all__ = [
    "health_router",
    "model_info_router",
    "predict_router",
    "auth_router",
]

