"""HeartAI FastAPI Clinical Intelligence Server.

Exposes high-performance REST APIs for cardiovascular risk prediction,
model metadata introspection, and automated Colab/Drive sync.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import ai_router, auth_router, health_router, model_info_router, predict_router
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import init_db
from app.ml import (
    ModelMetadata,
    PatientClinicalInput,
    PatientPredictionResult,
    predict_heart_disease,
    registry,
    transfer_manager,
)
from app.services.model_service import model_service
from logging_config import setup_logging

logger = setup_logging("INFO")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes database tables, ML artifacts, and registry on application startup."""
    logger.info("Initializing HeartAI Platform Services (v%s)...", settings.VERSION)

    # 1. Initialize Database
    try:
        init_db()
    except Exception as exc:
        logger.error("Database initialization failed: %s", exc)

    # 2. Load and verify calibrated production model artifact
    try:
        model_service.load_artifacts()
    except Exception as exc:
        logger.error("Failed to load production model artifacts: %s", exc)

    # 3. Maintain backward-compatible legacy registry
    try:
        count = registry.scan_and_register()
        logger.info("HeartAI legacy registry scanned %d models.", count)
    except Exception as exc:
        logger.warning("Legacy registry scan warning: %s", exc)

    logger.info("HeartAI API server startup complete. Listening on %s:%d", settings.APP_HOST, settings.APP_PORT)
    yield
    logger.info("HeartAI API server shutting down.")


app = FastAPI(
    title="HeartAI — Clinical Intelligence API",
    description="Cardiovascular Disease Risk Prediction & Healthcare Telemetry Platform",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Attach rate limiter to application state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware for modern frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for motion engine and styles
app.mount("/static", StaticFiles(directory="static"), name="static")


# Global safe exception handler: prevents internal paths or stack traces leaking
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> Response:
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )
    logger.error("Unhandled server exception at %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Telemetry has been logged."},
    )


# Mount Modular Production Routes
app.include_router(health_router)
app.include_router(model_info_router)
app.include_router(predict_router)
app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth")
app.include_router(ai_router, prefix=f"{settings.API_V1_STR}")


# ==============================================================================
# Legacy Compatibility Routes (UCI Cleveland 13-feature baseline & Drive sync)
# ==============================================================================


@app.get("/", tags=["System Health"])
def root_status():
    """Returns system operational status and active model metadata."""
    try:
        _, metadata = registry.get_active_model()
        active_info = {
            "model_id": metadata.model_id,
            "version": metadata.version,
            "architecture": metadata.architecture,
            "accuracy": metadata.metrics.accuracy,
            "roc_auc": metadata.metrics.roc_auc,
        }
    except Exception:
        active_info = {
            "model_id": "heartai-clinical-baseline",
            "version": "1.0.0",
            "status": "Running baseline clinical heuristic estimator",
        }

    return {
        "status": "online",
        "service": "HeartAI Clinical Intelligence Platform",
        "active_model": active_info,
    }


@app.get("/api/v1/models", response_model=list[ModelMetadata], tags=["Model Registry"])
def list_models():
    """Lists all verified and registered models available in the registry."""
    return registry.list_models()


@app.post(
    "/api/v1/predict",
    response_model=PatientPredictionResult,
    status_code=status.HTTP_200_OK,
    tags=["Clinical Inference"],
)
def predict_cardiac_risk(patient: PatientClinicalInput):
    """Calculates continuous cardiovascular disease risk probability and clinical factors."""
    try:
        result = predict_heart_disease(patient)
        return result
    except Exception as exc:
        logger.error("Inference exception: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cardiac inference error: {str(exc)}",
        ) from exc


class DriveSyncRequest(BaseModel):
    source_dir: str = Field(..., description="Path to Google Drive export folder containing model bundle")
    set_active: bool = Field(True, description="Automatically promote as active model")


@app.post("/api/v1/models/sync-drive", tags=["Model Transfer"])
def sync_model_from_drive(request: DriveSyncRequest):
    """Imports and validates an exported model bundle transferred from Google Drive."""
    try:
        metadata = transfer_manager.import_from_drive(request.source_dir, set_active=request.set_active)
        return {
            "status": "success",
            "message": f"Model {metadata.model_id} (v{metadata.version}) successfully imported and activated.",
            "metadata": metadata,
        }
    except Exception as err:
        logger.error("Drive sync failed: %s", err)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.APP_DEBUG)
