"""HeartAI System Health Endpoint."""

from __future__ import annotations

import time
from datetime import UTC, datetime

from fastapi import APIRouter, status

from app.core.config import settings
from app.db.session import check_db_connection
from app.schemas.health import DatabaseHealthStatus, HealthResponse, ModelHealthStatus
from app.services.model_service import model_service

router = APIRouter(tags=["System Telemetry"])

_SERVER_START_TIME = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health and Telemetry Check",
)
def get_system_health() -> HealthResponse:
    """Returns real-time health telemetry across the application, ML engine, and database."""
    uptime = time.time() - _SERVER_START_TIME
    db_ok, db_dialect = check_db_connection()
    model_status_dict = model_service.get_status()

    is_healthy = db_ok and model_status_dict.get("loaded", False)
    status_str = "healthy" if is_healthy else "degraded"

    return HealthResponse(
        status=status_str,
        service=settings.PROJECT_NAME + " Clinical Intelligence Platform",
        version=settings.VERSION,
        uptime_seconds=round(uptime, 2),
        timestamp=datetime.now(UTC).isoformat(),
        model=ModelHealthStatus(
            loaded=model_status_dict.get("loaded", False),
            model_id=str(model_status_dict.get("model_id", "unknown")),
            version=str(model_status_dict.get("version", "unknown")),
            sha256_verified=bool(model_status_dict.get("sha256_verified", False)),
            operating_threshold=float(model_status_dict.get("operating_threshold", 0.09)),
            preprocessor_sha256_verified=bool(model_status_dict.get("sha256_verified", False)),
            feature_count=int(model_status_dict.get("feature_count", 25)),
        ),
        database=DatabaseHealthStatus(
            connected=db_ok,
            dialect=db_dialect,
        ),
    )
