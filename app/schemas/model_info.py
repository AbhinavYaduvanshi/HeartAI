"""Model Metadata and Introspection Schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FeatureInfo(BaseModel):
    """Specification of an individual clinical input feature."""

    name: str = Field(..., description="Feature column identifier")
    type: str = Field(..., description="numerical | categorical_ordinal | binary")
    description: str = Field(..., description="Clinical codebook description")
    range_or_categories: str = Field(..., description="Valid bounds or category mapping")


class ModelInfoResponse(BaseModel):
    """Detailed metadata for the active calibrated cardiovascular model."""

    model_id: str = Field(..., description="Canonical model identifier")
    model_name: str = Field(..., description="Human-readable model name")
    version: str = Field(..., description="Model semantic version")
    architecture: str = Field(..., description="Scikit-Learn classifier architecture string")
    sha256_checksum: str = Field(..., description="Cryptographic SHA-256 artifact hash")
    is_calibrated: bool = Field(True, description="Whether probability calibration is active")
    calibration_method: str = Field("isotonic", description="Calibration algorithm")
    operating_threshold: float = Field(0.09, description="Decision threshold T for binary flag")
    training_records: int = Field(..., description="Number of training survey records")
    test_records: int = Field(..., description="Number of test survey records")
    dataset_source: str = Field(..., description="Survey dataset provenance")
    target_definition: str = Field(..., description="Formal clinical survey target definition")
    metrics: dict[str, Any] = Field(..., description="Standard evaluation metrics on test set")
    weighted_metrics: dict[str, Any] = Field(..., description="Complex survey-weighted evaluation metrics")
    latency_benchmark: dict[str, Any] = Field(..., description="Inference latency profile in microseconds")
    features: list[str] = Field(..., description="Ordered list of required 25 input features")
    features_detailed: list[FeatureInfo] = Field(default_factory=list, description="Detailed feature codebook specs")
    educational_disclaimer: str = Field(..., description="Standard scientific non-diagnostic disclaimer")

