"""Tests for HeartAI Clinical Input Validation."""

import pytest
from pydantic import ValidationError

from app.ml.validation import (
    PatientBRFSSInput,
    validate_input_dict,
)


@pytest.fixture
def valid_input():
    return {
        "Sex_Male": 1,
        "AgeCategory": 9,
        "BMI": 27.4,
        "BMICategory": 3,
        "Race": 1,
        "Education": 4,
        "Income": 7,
        "GeneralHealth": 3,
        "PhysicalHealthDays": 5.0,
        "MentalHealthDays": 0.0,
        "HighBP": 1,
        "HighCholesterol": 1,
        "StrokeHistory": 0,
        "Diabetes": 0,
        "KidneyDisease": 0,
        "Depression": 0,
        "Asthma": 0,
        "SmokerStatus": 3,
        "ECigStatus": 4,
        "PhysicalActivity": 1,
        "AlcoholDrinking": 0,
        "BingeDrinking": 0,
        "Checkup": 1,
        "MedCostObstacle": 0,
        "PersonalDoctor": 1,
    }


def test_valid_input_passes(valid_input):
    """Verify clean dictionary conforms to schema."""
    cleaned = validate_input_dict(valid_input)
    assert cleaned["BMI"] == 27.4
    assert cleaned["AgeCategory"] == 9


def test_bmi_out_of_bounds_raises(valid_input):
    """Verify extreme unphysiological BMI triggers validation error."""
    bad_data = valid_input.copy()
    bad_data["BMI"] = 150.0  # Above 80.0
    with pytest.raises(ValidationError):
        PatientBRFSSInput(**bad_data)

    bad_data["BMI"] = 8.0  # Below 12.0
    with pytest.raises(ValidationError):
        PatientBRFSSInput(**bad_data)


def test_age_category_out_of_bounds(valid_input):
    """Verify age category outside 1-13 raises ValidationError."""
    bad_data = valid_input.copy()
    bad_data["AgeCategory"] = 25  # Only 1-13 allowed
    with pytest.raises(ValidationError):
        PatientBRFSSInput(**bad_data)


def test_missing_required_features(valid_input):
    """Verify omitting required features raises ValidationError."""
    incomplete = valid_input.copy()
    del incomplete["Sex_Male"]
    del incomplete["AgeCategory"]
    with pytest.raises(ValidationError):
        PatientBRFSSInput(**incomplete)


def test_incorrect_data_types(valid_input):
    """Verify non-convertible data types raise ValidationError."""
    bad_type = valid_input.copy()
    bad_type["BMI"] = "not-a-number"
    with pytest.raises(ValidationError):
        PatientBRFSSInput(**bad_type)


def test_extra_unexpected_features_tolerated(valid_input):
    """Verify extraneous fields are safely ignored by pydantic model."""
    extra_data = valid_input.copy()
    extra_data["patient_name"] = "Confidential Patient"
    extra_data["hospital_id"] = 9999
    cleaned = validate_input_dict(extra_data)
    assert "patient_name" not in cleaned
    assert "hospital_id" not in cleaned
