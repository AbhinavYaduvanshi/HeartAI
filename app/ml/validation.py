"""HeartAI Clinical Feature Validation Engine.

Provides Pydantic schemas, physiological range checks, and categorical
boundary verification adhering to the CDC BRFSS 2023 codebook.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ClinicalInputValidationError(ValueError):
    """Raised when patient survey input violates codebook boundaries."""


class PatientBRFSSInput(BaseModel):
    """Cardiovascular risk survey feature vector matching CDC BRFSS 2023."""

    # Demographics
    Sex_Male: int = Field(..., ge=0, le=1, description="1 = Male, 0 = Female")
    AgeCategory: int = Field(..., ge=1, le=13, description="1: 18-24, 2: 25-29 ... 13: 80+")
    BMI: float = Field(..., ge=12.0, le=80.0, description="Body Mass Index in kg/m^2")
    BMICategory: int = Field(..., ge=1, le=4, description="1: Underweight, 2: Normal, 3: Overweight, 4: Obese")
    Race: int = Field(..., ge=1, le=8, description="CDC Race category (1: White, 2: Black ... 8: Hispanic)")
    Education: int = Field(..., ge=1, le=6, description="Education tier 1-6")
    Income: int = Field(..., ge=1, le=11, description="Household income bracket 1-11")

    # General & Functional Health
    GeneralHealth: int = Field(..., ge=1, le=5, description="1: Excellent, 2: Very Good, 3: Good, 4: Fair, 5: Poor")
    PhysicalHealthDays: float = Field(0.0, ge=0.0, le=30.0, description="Past 30 days physical health not good")
    MentalHealthDays: float = Field(0.0, ge=0.0, le=30.0, description="Past 30 days mental health not good")

    # Medical History (Flags: 1 = Yes, 0 = No)
    HighBP: int = Field(..., ge=0, le=1, description="Diagnosed with high blood pressure")
    HighCholesterol: int = Field(..., ge=0, le=1, description="Diagnosed with high cholesterol")
    StrokeHistory: int = Field(0, ge=0, le=1, description="Diagnosed with stroke")
    Diabetes: int = Field(0, ge=0, le=1, description="Diagnosed with diabetes")
    KidneyDisease: int = Field(0, ge=0, le=1, description="Diagnosed with kidney disease")
    Depression: int = Field(0, ge=0, le=1, description="Diagnosed with depressive disorder")
    Asthma: int = Field(0, ge=0, le=1, description="Diagnosed with asthma")

    # Lifestyle & Behaviors
    SmokerStatus: int = Field(..., ge=1, le=4, description="1: Daily, 2: Some days, 3: Former, 4: Never")
    ECigStatus: int = Field(..., ge=1, le=4, description="1: Daily, 2: Some days, 3: Not at all, 4: Never")
    PhysicalActivity: int = Field(..., ge=0, le=1, description="1: Active in past 30 days, 0: Inactive")
    AlcoholDrinking: int = Field(0, ge=0, le=1, description="1: Had alcohol past 30 days, 0: None")
    BingeDrinking: int = Field(0, ge=0, le=1, description="1: Binge drinking reported, 0: No")

    # Healthcare Access
    Checkup: int = Field(1, ge=1, le=5, description="1: Past year ... 5: 5+ years / never")
    MedCostObstacle: int = Field(0, ge=0, le=1, description="1: Needed doctor but could not afford, 0: No")
    PersonalDoctor: int = Field(1, ge=1, le=3, description="1: Yes one, 2: More than one, 3: No")

    @field_validator("BMI")
    @classmethod
    def validate_bmi_range(cls, v: float) -> float:
        if v < 12.0 or v > 80.0:
            raise ClinicalInputValidationError(f"BMI {v} is outside physiological limits (12-80).")
        return round(float(v), 2)


def validate_input_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Validates raw dictionary input against PatientBRFSSInput schema."""
    validated = PatientBRFSSInput(**data)
    return validated.model_dump()
