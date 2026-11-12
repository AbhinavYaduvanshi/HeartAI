"""HeartAI Machine Learning Package.

Multi-format model loading, metadata enforcement, and clinical inference.
"""

from app.ml.model_loader import (
    ModelCompatibilityError,
    ModelSecurityError,
    compute_file_sha256,
    load_model_artifact,
    load_model_bundle,
    load_model_metadata,
)
from app.ml.model_metadata import (
    CANONICAL_HEART_FEATURES,
    ClinicalRiskCategory,
    FeatureSpecification,
    ModelArtifactFormat,
    ModelMetadata,
    ModelMetrics,
)
from app.ml.model_registry import ModelRegistry, registry
from app.ml.predict import (
    PatientClinicalInput,
    PatientPredictionResult,
    categorize_risk_score,
    predict_heart_disease,
)
from app.ml.transfer_sync import ModelTransferManager, transfer_manager

__all__ = [
    "CANONICAL_HEART_FEATURES",
    "ClinicalRiskCategory",
    "FeatureSpecification",
    "ModelArtifactFormat",
    "ModelMetadata",
    "ModelMetrics",
    "ModelSecurityError",
    "ModelCompatibilityError",
    "compute_file_sha256",
    "load_model_metadata",
    "load_model_artifact",
    "load_model_bundle",
    "ModelRegistry",
    "registry",
    "PatientClinicalInput",
    "PatientPredictionResult",
    "categorize_risk_score",
    "predict_heart_disease",
    "ModelTransferManager",
    "transfer_manager",
]
