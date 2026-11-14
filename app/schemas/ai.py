"""HeartAI Gemini Generative AI Schemas.

Pydantic schemas for AI assistant interactions, health metric explanations,
risk interpretation, structured clinical education, and status reporting.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

STANDARD_AI_DISCLAIMER = (
    "Educational Cardiovascular Research Assistant: This information is for general "
    "educational purposes only. HeartAI does not provide medical diagnoses, treatment plans, "
    "or prescriptions. Always consult a qualified physician or healthcare provider for "
    "medical concerns. In an acute emergency, call your local emergency services (e.g. 911 / 112) immediately."
)


class AIStatusResponse(BaseModel):
    """Status of Google Gemini integration and client readiness."""

    configured: bool = Field(..., description="Whether a valid, non-placeholder API key is configured")
    model: str = Field(..., description="Configured Gemini model identifier")
    service: str = Field("HeartAI Clinical Education Assistant", description="AI service name")
    message: str = Field(..., description="Current status description or authorization instructions")
    authorization_url: str = Field(
        "https://aistudio.google.com/docs/api-key",
        description="Official Google AI Studio documentation and API key generation URL",
    )


class StructuredAIAdvice(BaseModel):
    """Structured educational response conforming to cardiology guidelines."""

    title: str = Field("Heart Health Guidance", description="Title of the educational response")
    summary: str = Field(..., description="Summary of evidence-based cardiovascular education")
    key_points: list[str] = Field(default_factory=list, description="Key educational takeaways")
    lifestyle_recommendations: list[str] = Field(
        default_factory=list,
        description="General cardiovascular lifestyle factors (nutrition, exercise, sleep)",
    )
    questions_for_doctor: list[str] = Field(
        default_factory=list,
        description="Informed questions the patient may discuss with their primary physician",
    )
    emergency_guidance: str | None = Field(
        None,
        description="Emergency instructions if acute symptoms are mentioned",
    )
    disclaimer: str = Field(STANDARD_AI_DISCLAIMER, description="Mandatory medical disclaimer")


class AIChatRequest(BaseModel):
    """Inbound chat prompt for the HeartAI Healthcare Assistant."""

    message: str = Field(
        ...,
        min_length=2,
        max_length=2000,
        description="User query regarding heart health, cardiology concepts, or metrics",
    )
    conversation_history: list[dict[str, str]] | None = Field(
        None,
        description="Optional list of previous messages in format [{'role': 'user'|'model', 'text': '...'}]",
    )
    user_consent_given: bool = Field(
        False,
        description="Affirmative consent for context personalization",
    )


class AIChatResponse(BaseModel):
    """Outbound chat response from the HeartAI Healthcare Assistant."""

    response_text: str = Field(..., description="Natural language response")
    structured_advice: StructuredAIAdvice | None = Field(
        None,
        description="Parsed structured breakdown if applicable",
    )
    emergency_flag: bool = Field(
        False,
        description="True if potential acute emergency symptoms were detected",
    )
    emergency_guidance: str | None = Field(
        None,
        description="Immediate emergency guidance if acute symptoms detected",
    )
    model_used: str = Field(..., description="Gemini model identifier used for generation")
    disclaimer: str = Field(STANDARD_AI_DISCLAIMER, description="Mandatory educational disclaimer")


class MetricExplanationRequest(BaseModel):
    """Request for cardiovascular metric interpretation."""

    metric_name: str = Field(
        ...,
        description="Name of the health metric (e.g. 'Blood Pressure', 'BMI', 'Cholesterol', 'SpO2')",
    )
    metric_value: float | None = Field(
        None,
        description="Optional numeric metric value for context",
    )
    unit: str | None = Field(
        None,
        description="Optional unit of measurement (e.g. 'mmHg', 'kg/m²', 'mg/dL', '%')",
    )


class RiskExplanationRequest(BaseModel):
    """Request to explain ML model prediction uncertainty and limitations."""

    estimated_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Continuous calibrated probability output from HeartAI model",
    )
    binary_classification: int = Field(
        ...,
        ge=0,
        le=1,
        description="Classification flag based on operating threshold (0 or 1)",
    )
    operating_threshold: float = Field(
        0.09,
        description="Calibrated operating threshold (default 0.09)",
    )
    user_consent_given: bool = Field(
        False,
        description="Affirmative user consent to incorporate survey context",
    )


class PersonalizedEducationRequest(BaseModel):
    """Request for evidence-based lifestyle education based on survey features."""

    user_consent_given: bool = Field(
        False,
        description="Strict prerequisite: affirmative consent required to process features",
    )
    consent_terms_version: str | None = Field(
        None,
        description="Informed consent terms version (e.g. '2026.1')",
    )
    survey_features: dict[str, Any] = Field(
        default_factory=dict,
        description="Consented demographic/lifestyle features (e.g. BMI, SmokerStatus, PhysicalActivity)",
    )
