"""Prediction Request and Response Schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.ml.validation import PatientBRFSSInput

STANDARD_RESEARCH_LIMITATIONS = [
    "Educational research prototype only: NOT clinically validated or intended for diagnosis.",
    "Survey data source (CDC BRFSS 2023): self-reported historical disease status, not prospective event risk.",
    "Target leakage excluded: model does not use source clinical diagnosis questions (CVDINFR4, CVDCRHD4).",
    "Survey sampling bias: individual estimates do not incorporate complex multi-stage sampling weights (_LLCPWT).",
    "Model probabilities reflect population correlation, not individual biological causality.",
]

DEFAULT_PRIVACY_NOTICE = (
    "Informed Telemetry Policy: When affirmative consent is granted, HeartAI persists only a "
    "server-side keyed HMAC-SHA256 digest of normalized feature values, calculated probabilities, and "
    "classification thresholds for calibration auditing. Raw survey responses are never stored. "
    "Users may delete their prediction history anytime via DELETE /api/v1/auth/history."
)


class PredictionRequest(PatientBRFSSInput):
    """Cardiovascular risk prediction request adhering to CDC BRFSS 2023 survey schema."""

    user_consent_given: bool = Field(
        False,
        description="Explicit affirmative user consent to store keyed pseudonymized audit digest in research telemetry",
    )
    consent_terms_version: str | None = Field(
        None,
        description="Version identifier of the informed consent notice acknowledged by the user (e.g. '2026.1')",
    )
    client_id: str | None = Field(
        None,
        description="Optional client identifier for ephemeral telemetry tracking",
    )


class PredictionResponse(BaseModel):
    """Standardized educational cardiovascular estimation response.

    Adheres strictly to scientific non-diagnostic terminology.
    Never describes output as future heart attack risk or clinical diagnosis.
    """

    metric_label: str = Field(
        "Estimated probability of reported historical cardiovascular disease",
        description="Scientific metric definition: historical self-reported status, not future event risk",
    )
    estimated_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Continuous calibrated probability (0.0 to 1.0)",
    )
    estimated_probability_percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Probability expressed as percentage (0.0% to 100.0%)",
    )
    binary_classification: int = Field(
        ...,
        ge=0,
        le=1,
        description="Binary flag evaluated at calibrated operating threshold (1 if prob >= threshold else 0)",
    )
    operating_threshold: float = Field(
        0.09,
        description="Operating threshold used for binary classification",
    )
    model_name: str = Field(
        ...,
        description="Name of the evaluated ML model",
    )
    model_version: str = Field(
        ...,
        description="Model semantic version",
    )
    calibration_status: str = Field(
        "calibrated_isotonic_cv5",
        description="Calibration methodology ensuring well-aligned probabilities",
    )
    output_type: str = Field(
        "educational_estimate",
        description="Explicit indicator of educational non-clinical purpose",
    )
    clinical_validation: bool = Field(
        False,
        description="Always False: educational research prototype",
    )
    consent_recorded: bool = Field(
        False,
        description="True if user provided explicit affirmative consent with valid terms version and record was persisted",
    )
    consent_terms_version: str | None = Field(
        None,
        description="Version of informed consent terms under which record was processed",
    )
    privacy_notice: str = Field(
        DEFAULT_PRIVACY_NOTICE,
        description="Mandatory privacy and retention disclosure",
    )
    limitations: list[str] = Field(
        default_factory=lambda: list(STANDARD_RESEARCH_LIMITATIONS),
        description="Documented methodological and epidemiological caveats",
    )
    educational_disclaimer: str = Field(
        "Educational research estimate; not a clinical diagnostic device. "
        "Evaluates self-reported historical survey patterns, not future incident cardiovascular events.",
        description="Mandatory ethical and clinical non-diagnostic disclosure",
    )
