"""HeartAI FastAPI Clinical Intelligence Server.

Exposes high-performance REST APIs for cardiovascular risk prediction,
model metadata introspection, and automated Colab/Drive sync.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.ml import (
    ModelMetadata,
    PatientClinicalInput,
    PatientPredictionResult,
    predict_heart_disease,
    registry,
    transfer_manager,
)
from logging_config import setup_logging

logger = setup_logging("INFO")

app = FastAPI(
    title="HeartAI — Clinical Intelligence API",
    description="Cardiovascular Disease Risk Prediction & Healthcare Telemetry Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for modern frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    """Initializes ML model registry on server startup."""
    count = registry.scan_and_register()
    logger.info("HeartAI API server initialized with %d registered models.", count)


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

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
