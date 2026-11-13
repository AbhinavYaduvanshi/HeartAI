"""HeartAI Machine Learning Package.

Multi-format model loading, metadata enforcement, and clinical inference.
"""

from app.ml.custom_ensembles import (
    EnrichedRandomForestClassifier,
    TreeWeightedRandomForestClassifier,
)
from app.ml.explainability import (
    calculate_demographic_fairness,
    extract_feature_importances,
)
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
    EducationalPredictionResponse,
    PatientClinicalInput,
    PatientPredictionResult,
    categorize_risk_score,
    predict_educational_estimate,
    predict_heart_disease,
)
from app.ml.preprocessing import (
    ALL_INPUT_FEATURES,
    build_preprocessing_pipeline,
    prepare_feature_dataframe,
)
from app.ml.transfer_sync import ModelTransferManager, transfer_manager
from app.ml.validation import (
    ClinicalInputValidationError,
    PatientBRFSSInput,
    validate_input_dict,
)

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
    "EducationalPredictionResponse",
    "predict_educational_estimate",
    "ModelTransferManager",
    "transfer_manager",
    "EnrichedRandomForestClassifier",
    "TreeWeightedRandomForestClassifier",
    "build_preprocessing_pipeline",
    "prepare_feature_dataframe",
    "ALL_INPUT_FEATURES",
    "PatientBRFSSInput",
    "validate_input_dict",
    "ClinicalInputValidationError",
    "extract_feature_importances",
    "calculate_demographic_fairness",
]
