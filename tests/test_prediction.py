"""Tests for HeartAI Educational Prediction Engine."""

import pytest

from app.ml.predict import (
    EducationalPredictionResponse,
    predict_educational_estimate,
)
from app.ml.validation import PatientBRFSSInput


@pytest.fixture
def sample_patient_dict():
    """Standard healthy sample respondent dictionary."""
    return {
        "Sex_Male": 1,
        "AgeCategory": 8,  # 55-59
        "BMI": 26.5,
        "BMICategory": 3,
        "Race": 1,
        "Education": 5,
        "Income": 8,
        "GeneralHealth": 2,
        "PhysicalHealthDays": 0.0,
        "MentalHealthDays": 2.0,
        "HighBP": 0,
        "HighCholesterol": 0,
        "StrokeHistory": 0,
        "Diabetes": 0,
        "KidneyDisease": 0,
        "Depression": 0,
        "Asthma": 0,
        "SmokerStatus": 4,  # Never
        "ECigStatus": 4,
        "PhysicalActivity": 1,
        "AlcoholDrinking": 1,
        "BingeDrinking": 0,
        "Checkup": 1,
        "MedCostObstacle": 0,
        "PersonalDoctor": 1,
    }


def test_prediction_output_structure(sample_patient_dict):
    """Verify response complies with Step 13 required schema."""
    result = predict_educational_estimate(sample_patient_dict)
    assert isinstance(result, EducationalPredictionResponse)
    assert result.output_type == "educational_estimate"
    assert result.clinical_validation is False
    assert result.prediction in [0, 1]
    assert 0.0 <= result.estimated_probability <= 1.0
    assert len(result.limitations) >= 3


def test_prediction_with_pydantic_instance(sample_patient_dict):
    """Verify prediction accepts PatientBRFSSInput directly."""
    patient_obj = PatientBRFSSInput(**sample_patient_dict)
    result = predict_educational_estimate(patient_obj)
    assert isinstance(result, EducationalPredictionResponse)
    assert result.model_name in ["best_model", "logistic_regression"]


def test_prediction_multiple_algorithms(sample_patient_dict):
    """Verify prediction works with different exported algorithm models."""
    algorithms = [
        "best_model",
        "random_forest",
        "catboost",
        "gradient_boosting",
        "enriched_random_forest",
        "tree_weighted_random_forest",
    ]
    for algo in algorithms:
        res = predict_educational_estimate(sample_patient_dict, model_name=algo)
        assert res.prediction in [0, 1]
        assert 0.0 <= res.estimated_probability <= 1.0


def test_prediction_high_risk_profile(sample_patient_dict):
    """Verify elevated probability for high-burden cardiovascular risk profile."""
    high_risk_data = sample_patient_dict.copy()
    high_risk_data.update({
        "AgeCategory": 12,  # 75-79
        "GeneralHealth": 5,  # Poor
        "HighBP": 1,
        "HighCholesterol": 1,
        "StrokeHistory": 1,
        "Diabetes": 1,
        "SmokerStatus": 1,  # Everyday
        "PhysicalActivity": 0,
    })
    result = predict_educational_estimate(high_risk_data)
    assert result.estimated_probability > 0.50
    assert result.prediction == 1
