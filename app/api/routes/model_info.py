"""HeartAI Model Metadata & Inspection Route."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, status

from app.schemas.model_info import FeatureInfo, ModelInfoResponse
from app.services.model_service import model_service

router = APIRouter(tags=["Model Governance"])

# 25 Canonical CDC BRFSS feature definitions
FEATURE_DEFINITIONS: list[dict[str, str]] = [
    {"name": "BMI", "type": "numerical", "description": "Body Mass Index in kg/m^2", "range_or_categories": "12.0 - 80.0"},
    {"name": "PhysicalHealthDays", "type": "numerical", "description": "Past 30 days physical health not good", "range_or_categories": "0.0 - 30.0"},
    {"name": "MentalHealthDays", "type": "numerical", "description": "Past 30 days mental health not good", "range_or_categories": "0.0 - 30.0"},
    {"name": "AgeCategory", "type": "categorical_ordinal", "description": "13 five-year age brackets (1: 18-24 ... 13: 80+)", "range_or_categories": "1 - 13"},
    {"name": "BMICategory", "type": "categorical_ordinal", "description": "CDC BMI weight tiers (1: Underweight ... 4: Obese)", "range_or_categories": "1 - 4"},
    {"name": "Race", "type": "categorical_ordinal", "description": "CDC Race categories (1: White ... 8: Hispanic)", "range_or_categories": "1 - 8"},
    {"name": "Education", "type": "categorical_ordinal", "description": "Educational attainment levels", "range_or_categories": "1 - 6"},
    {"name": "Income", "type": "categorical_ordinal", "description": "Annual household income brackets", "range_or_categories": "1 - 11"},
    {"name": "GeneralHealth", "type": "categorical_ordinal", "description": "Self-reported overall health (1: Excellent ... 5: Poor)", "range_or_categories": "1 - 5"},
    {"name": "SmokerStatus", "type": "categorical_ordinal", "description": "Tobacco cigarette frequency (1: Daily ... 4: Never)", "range_or_categories": "1 - 4"},
    {"name": "ECigStatus", "type": "categorical_ordinal", "description": "E-cigarette / vaping frequency (1: Daily ... 4: Never)", "range_or_categories": "1 - 4"},
    {"name": "Checkup", "type": "categorical_ordinal", "description": "Recency of routine physical exam (1: <1yr ... 5: 5+yrs/never)", "range_or_categories": "1 - 5"},
    {"name": "PersonalDoctor", "type": "categorical_ordinal", "description": "Primary healthcare provider status (1: Yes one, 2: More, 3: None)", "range_or_categories": "1 - 3"},
    {"name": "Sex_Male", "type": "binary", "description": "Biological sex (1: Male, 0: Female)", "range_or_categories": "0, 1"},
    {"name": "HighBP", "type": "binary", "description": "History of physician-diagnosed high blood pressure", "range_or_categories": "0, 1"},
    {"name": "HighCholesterol", "type": "binary", "description": "History of physician-diagnosed high cholesterol", "range_or_categories": "0, 1"},
    {"name": "StrokeHistory", "type": "binary", "description": "History of physician-diagnosed cerebrovascular accident (stroke)", "range_or_categories": "0, 1"},
    {"name": "Diabetes", "type": "binary", "description": "History of physician-diagnosed diabetes mellitus", "range_or_categories": "0, 1"},
    {"name": "KidneyDisease", "type": "binary", "description": "History of physician-diagnosed chronic kidney disease", "range_or_categories": "0, 1"},
    {"name": "Depression", "type": "binary", "description": "History of physician-diagnosed depressive disorder", "range_or_categories": "0, 1"},
    {"name": "Asthma", "type": "binary", "description": "History of physician-diagnosed asthma", "range_or_categories": "0, 1"},
    {"name": "PhysicalActivity", "type": "binary", "description": "Physical exercise or activity reported during past 30 days", "range_or_categories": "0, 1"},
    {"name": "AlcoholDrinking", "type": "binary", "description": "Any alcoholic beverage consumption during past 30 days", "range_or_categories": "0, 1"},
    {"name": "BingeDrinking", "type": "binary", "description": "Binge drinking reported in past 30 days", "range_or_categories": "0, 1"},
    {"name": "MedCostObstacle", "type": "binary", "description": "Past 12 months needed to see doctor but could not due to cost", "range_or_categories": "0, 1"},
]


@router.get(
    "/model-info",
    response_model=ModelInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Active Model Architecture, Calibration & Governance Metadata",
)
def get_model_information() -> ModelInfoResponse:
    """Returns comprehensive metadata, calibration metrics, and non-diagnostic disclaimers."""
    meta = model_service.get_metadata()

    # Load feature names list
    feat_path = Path("models/feature_names.json")
    if feat_path.exists():
        with open(feat_path, encoding="utf-8") as f:
            features = json.load(f)
    else:
        features = [f["name"] for f in FEATURE_DEFINITIONS]

    detailed_features = [FeatureInfo(**d) for d in FEATURE_DEFINITIONS]

    calibration_info = meta.get("calibration", {})

    return ModelInfoResponse(
        model_id=str(meta.get("model_id", "heartai-calibrated-v2")),
        model_name=str(meta.get("model_name", "HeartAI BRFSS Research Classifier")),
        version=str(meta.get("version", "2.1.0")),
        architecture=str(meta.get("architecture", "CalibratedClassifierCV(LogisticRegression, isotonic, 5-fold)")),
        sha256_checksum=str(meta.get("sha256_checksum", "")),
        is_calibrated=bool(calibration_info.get("is_calibrated", True)),
        calibration_method=str(calibration_info.get("method", "isotonic")),
        operating_threshold=float(calibration_info.get("optimal_screening_threshold", 0.09)),
        training_records=int(meta.get("training_records", 318296)),
        test_records=int(meta.get("test_records", 79574)),
        dataset_source=str(meta.get("dataset_source", "CDC BRFSS 2023")),
        target_definition=str(
            meta.get(
                "target_definition",
                "Estimated probability of reported historical cardiovascular disease (_MICHD: 1=Yes, 0=No)",
            )
        ),
        metrics=dict(meta.get("metrics", {})),
        weighted_metrics=dict(meta.get("weighted_metrics", {})),
        latency_benchmark=dict(meta.get("latency_benchmark", {})),
        features=features,
        features_detailed=detailed_features,
        educational_disclaimer=str(
            meta.get(
                "educational_disclaimer",
                "Educational research estimate; not a clinical diagnostic device. "
                "Evaluates self-reported historical survey patterns, not future incident cardiovascular events.",
            )
        ),
    )
