"""Health Check Response Schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelHealthStatus(BaseModel):
    """Integrity and availability status of the active ML artifact."""

    loaded: bool = Field(..., description="Whether model is loaded in memory")
    model_id: str = Field(..., description="Active model identifier")
    version: str = Field(..., description="Active model version")
    sha256_verified: bool = Field(..., description="Integrity check result against metadata hash")
    operating_threshold: float = Field(0.09, description="Calibrated operating threshold")
    preprocessor_sha256_verified: bool = Field(True, description="Preprocessing pipeline integrity status")
    feature_count: int = Field(25, description="Validated input feature count")


class DatabaseHealthStatus(BaseModel):
    """Database connectivity status."""

    connected: bool = Field(..., description="Whether database connection succeeded")
    dialect: str = Field(..., description="Database dialect (e.g. sqlite, postgresql)")


class HealthResponse(BaseModel):
    """Overall system health and telemetry response."""

    status: str = Field("healthy", description="Overall health state (healthy, degraded, unhealthy)")
    service: str = Field("HeartAI Clinical Intelligence Platform", description="Service name")
    version: str = Field("2.1.0", description="Backend service semantic version")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    timestamp: str = Field(..., description="ISO 8601 server timestamp")
    model: ModelHealthStatus = Field(..., description="ML model health details")
    database: DatabaseHealthStatus = Field(..., description="Database health details")
