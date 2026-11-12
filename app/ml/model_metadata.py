"""HeartAI Model Metadata & Validation Schema.

Provides Pydantic schemas for machine learning model versioning, feature
specifications, performance metrics, and clinical compatibility validation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ModelArtifactFormat(StrEnum):
    """Supported serialized model artifact file formats."""

    JOBLIB = "joblib"
    PICKLE = "pkl"
    PYTORCH = "pt"


class ClinicalRiskCategory(StrEnum):
    """Clinical stratification tiers for cardiovascular disease risk."""

    LOW = "Low Risk"
    BORDERLINE = "Borderline Risk"
    INTERMEDIATE = "Intermediate Risk"
    HIGH = "High Risk"


class FeatureSpecification(BaseModel):
    """Metadata schema defining an expected input feature."""

    name: str = Field(..., description="Canonical clinical feature identifier (e.g. 'trestbps')")
    data_type: str = Field("float64", description="Expected primitive type: float64, int64, str")
    display_name: str = Field(..., description="Human-readable clinical label")
    unit: str | None = Field(None, description="Clinical measurement unit (e.g. 'mmHg', 'mg/dl')")
    min_value: float | None = Field(None, description="Physiological minimum bound")
    max_value: float | None = Field(None, description="Physiological maximum bound")
    allowed_categories: list[Any] | None = Field(None, description="Permitted categorical values if applicable")


class ModelMetrics(BaseModel):
    """Quantitative performance metrics verified during validation."""

    accuracy: float = Field(..., ge=0.0, le=1.0)
    roc_auc: float = Field(..., ge=0.0, le=1.0)
    sensitivity_recall: float = Field(..., ge=0.0, le=1.0, description="True Positive Rate (Arrhythmia/CAD)")
    specificity: float = Field(..., ge=0.0, le=1.0, description="True Negative Rate")
    f1_score: float = Field(..., ge=0.0, le=1.0)
    precision: float = Field(..., ge=0.0, le=1.0)
    brier_score: float | None = Field(None, ge=0.0, le=1.0, description="Probabilistic calibration metric")


class ModelMetadata(BaseModel):
    """Comprehensive metadata manifest accompanying every HeartAI exported model."""

    model_id: str = Field(..., description="Unique slug (e.g. 'heartai-xgboost-v1')")
    model_name: str = Field(..., description="Human-readable model name")
    version: str = Field(..., description="Semantic version string (e.g. '1.0.0')")
    architecture: str = Field(..., description="Algorithm type: XGBoost, RandomForest, PyTorch-MLP")
    artifact_format: ModelArtifactFormat = Field(..., description="File format (.pkl, .joblib, .pt)")
    artifact_filename: str = Field(..., description="Filename inside model storage directory")
    sha256_checksum: str = Field(..., description="Cryptographic SHA-256 checksum of the artifact")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    framework_versions: dict[str, str] = Field(
        default_factory=dict,
        description="Versions of python, scikit-learn, torch, xgboost used during training",
    )
    dataset_source: str = Field(
        "UCI Heart Disease & Framingham Benchmark",
        description="Clinical dataset provenance",
    )
    features: list[FeatureSpecification] = Field(
        ...,
        description="Ordered list of required input clinical features",
    )
    metrics: ModelMetrics = Field(..., description="Evaluation benchmark metrics")
    tags: list[str] = Field(default_factory=list)
    is_active_production: bool = Field(False)

    @field_validator("sha256_checksum")
    @classmethod
    def validate_checksum_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if len(clean) != 64:
            raise ValueError(f"Invalid SHA-256 checksum length ({len(clean)} chars; expected 64).")
        return clean

    def get_feature_names(self) -> list[str]:
        """Returns ordered list of feature identifiers."""
        return [f.name for f in self.features]


# ==============================================================================
# CANONICAL UCI CLEVELAND HEART DISEASE FEATURE SCHEMAS
# ==============================================================================

CANONICAL_HEART_FEATURES: list[FeatureSpecification] = [
    FeatureSpecification(name="age", data_type="float64", display_name="Age", unit="years", min_value=18, max_value=120),
    FeatureSpecification(name="sex", data_type="int64", display_name="Biological Sex", unit=None, min_value=0, max_value=1, allowed_categories=[0, 1]),
    FeatureSpecification(name="cp", data_type="int64", display_name="Chest Pain Type (0-3)", unit=None, min_value=0, max_value=3, allowed_categories=[0, 1, 2, 3]),
    FeatureSpecification(name="trestbps", data_type="float64", display_name="Resting Blood Pressure", unit="mmHg", min_value=70, max_value=240),
    FeatureSpecification(name="chol", data_type="float64", display_name="Serum Cholesterol", unit="mg/dl", min_value=100, max_value=600),
    FeatureSpecification(name="fbs", data_type="int64", display_name="Fasting Blood Sugar > 120 mg/dl", unit=None, min_value=0, max_value=1, allowed_categories=[0, 1]),
    FeatureSpecification(name="restecg", data_type="int64", display_name="Resting Electrocardiogram (0-2)", unit=None, min_value=0, max_value=2, allowed_categories=[0, 1, 2]),
    FeatureSpecification(name="thalach", data_type="float64", display_name="Maximum Heart Rate Achieved", unit="bpm", min_value=50, max_value=240),
    FeatureSpecification(name="exang", data_type="int64", display_name="Exercise Induced Angina", unit=None, min_value=0, max_value=1, allowed_categories=[0, 1]),
    FeatureSpecification(name="oldpeak", data_type="float64", display_name="ST Depression Induced by Exercise", unit="mm", min_value=0.0, max_value=8.0),
    FeatureSpecification(name="slope", data_type="int64", display_name="Slope of Peak Exercise ST Segment (0-2)", unit=None, min_value=0, max_value=2, allowed_categories=[0, 1, 2]),
    FeatureSpecification(name="ca", data_type="int64", display_name="Number of Major Vessels (0-4)", unit=None, min_value=0, max_value=4, allowed_categories=[0, 1, 2, 3, 4]),
    FeatureSpecification(name="thal", data_type="int64", display_name="Thallium Stress Scintigraphy (0-3)", unit=None, min_value=0, max_value=3, allowed_categories=[0, 1, 2, 3]),
]
