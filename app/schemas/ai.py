"""HeartAI Generative AI Schemas — Aarogya Saathi (आरोग्य साथी).

Pydantic schemas for Aarogya Saathi conversational assistant,
symptom assessment, health metric explanations, risk interpretation,
and trusted consent-gated clinical education.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

STANDARD_AI_DISCLAIMER = (
    "Aarogya Saathi (आरोग्य साथी) — HeartAI Educational Cardiovascular Research Assistant & Health Companion: "
    "This guidance is strictly for general health education and research. HeartAI does NOT "
    "provide medical diagnoses, treatment plans, prescriptions, or medication changes. "
    "Always consult a qualified doctor or cardiologist for personalized medical decisions. "
    "In an acute emergency, call your local emergency services (112 in India, 911 in US/Canada, 999 in UK) immediately."
)

EMERGENCY_CONTACT_NUMBERS = {
    "India": "112 (National Emergency Number) / 102 (Ambulance)",
    "US / Canada": "911",
    "United Kingdom": "999",
    "Europe": "112",
    "Australia": "000",
}


class AIStatusResponse(BaseModel):
    """Status of Google Gemini integration and Aarogya Saathi client readiness."""

    configured: bool = Field(..., description="Whether a valid, non-placeholder API key is configured")
    model: str = Field(..., description="Configured Gemini model identifier")
    assistant_name: str = Field(
        "Aarogya Saathi (आरोग्य साथी)",
        description="Official name of the HeartAI healthcare companion",
    )
    service: str = Field(
        "HeartAI Clinical Education Assistant",
        description="AI service tier description",
    )
    authenticated_client: bool = Field(
        False,
        description="Whether the client making the request is authenticated",
    )
    message: str = Field(..., description="Current status description or authorization instructions")
    authorization_url: str = Field(
        "https://aistudio.google.com/docs/api-key",
        description="Official Google AI Studio documentation and API key generation URL",
    )


class ConversationTurn(BaseModel):
    """Validated single turn of conversation history."""

    role: str = Field(
        ...,
        pattern="^(user|model|assistant)$",
        description="Speaker role: 'user' or 'model'/'assistant'. System injection is rejected.",
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Turn message text sanitized from PII",
    )


class AIChatRequest(BaseModel):
    """Inbound chat prompt for Aarogya Saathi (आरोग्य साथी)."""

    message: str = Field(
        ...,
        min_length=2,
        max_length=2000,
        description="User query regarding HeartAI, heart health, cardiovascular symptoms, or metrics",
    )
    conversation_history: list[ConversationTurn] | None = Field(
        None,
        max_length=6,
        description="Bounded list of previous messages (max 6 turns to avoid context manipulation)",
    )
    feature_context: str | None = Field(
        None,
        description="HeartAI application feature in use (e.g. 'hero', 'assessment', 'metrics', 'analytics', 'doctors', 'symptoms')",
    )
    context_data: dict[str, Any] | None = Field(
        None,
        description="Authorized minimal contextual data from the active HeartAI view",
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


class AIChatResponse(BaseModel):
    """Outbound chat response from Aarogya Saathi."""

    response_text: str = Field(..., description="Natural language educational response")
    assistant_name: str = Field("Aarogya Saathi (आरोग्य साथी)", description="Assistant identifier")
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
    domain_restricted: bool = Field(
        False,
        description="True if the user's inquiry was out-of-domain and blocked before Gemini",
    )
    model_used: str = Field(..., description="Gemini model identifier used for generation")
    disclaimer: str = Field(STANDARD_AI_DISCLAIMER, description="Mandatory educational disclaimer")


class MetricExplanationRequest(BaseModel):
    """Request for cardiovascular metric interpretation."""

    metric_name: str = Field(
        ...,
        min_length=2,
        max_length=64,
        description="Name of the health metric (e.g. 'Blood Pressure', 'BMI', 'Cholesterol', 'SpO2')",
    )
    metric_value: float | None = Field(
        None,
        description="Optional numeric metric value for context",
    )
    unit: str | None = Field(
        None,
        max_length=16,
        description="Optional unit of measurement (e.g. 'mmHg', 'kg/m²', '%', 'bpm')",
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
    feature_context: dict[str, Any] | None = Field(
        None,
        description="Optional consented summary of survey indicators",
    )


class SymptomSeverity(StrEnum):
    """User-reported symptom severity tier."""

    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    VERY_SEVERE = "very_severe"


class SymptomProgression(StrEnum):
    """Symptom trend over time."""

    GETTING_BETTER = "getting_better"
    GETTING_WORSE = "getting_worse"
    UNCHANGED = "unchanged"
    RAPIDLY_WORSENING = "rapidly_worsening"


class SymptomUrgencyCategory(StrEnum):
    """Conservative urgency classification for symptom guidance."""

    EMERGENCY = "EMERGENCY"
    URGENT = "URGENT"
    ROUTINE = "ROUTINE"
    NON_CARDIOVASCULAR_OR_UNCERTAIN = "NON_CARDIOVASCULAR_OR_UNCERTAIN"


class SymptomAssessmentInput(BaseModel):
    """Structured user input for cardiovascular symptom educational assessment."""

    symptoms_experienced: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Free-text description of symptoms experienced by user",
    )
    onset_time: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="When symptoms started (e.g. '1 hour ago', 'yesterday morning', 'gradual over 2 weeks')",
    )
    is_ongoing: bool = Field(
        True,
        description="Whether symptoms are currently ongoing (True) or intermittent (False)",
    )
    severity: SymptomSeverity = Field(
        SymptomSeverity.MILD,
        description="User-reported severity: 'mild', 'moderate', or 'severe'",
    )
    associated_symptoms: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Optional list of associated symptoms (e.g. sweating, dizziness, nausea)",
    )
    progression: SymptomProgression = Field(
        SymptomProgression.UNCHANGED,
        description="Symptom progression: 'getting_better', 'getting_worse', or 'unchanged'",
    )


class SymptomAnalysisResponse(BaseModel):
    """Conservative, non-diagnostic educational analysis of user symptoms."""

    symptom_summary: str = Field(..., description="Summary of user-described symptoms")
    general_cardiovascular_relevance: str = Field(
        ...,
        description="Educational discussion of how symptoms relate to heart and vascular physiology",
    )
    warning_signs_identified: list[str] = Field(
        default_factory=list,
        description="Specific warning signs that may warrant urgent or emergency medical evaluation",
    )
    urgency_category: SymptomUrgencyCategory = Field(
        ...,
        description="Conservative urgency tier (EMERGENCY, URGENT, ROUTINE, or UNCERTAIN)",
    )
    suggested_next_action: str = Field(
        ...,
        description="Actionable next step (e.g. seek emergency medical care, call doctor today, routine checkup)",
    )
    is_emergency: bool = Field(
        False,
        description="True if potentially life-threatening emergency symptoms were flagged",
    )
    emergency_contacts: dict[str, str] = Field(
        default_factory=lambda: EMERGENCY_CONTACT_NUMBERS,
        description="Official emergency telephone numbers by country with India (112) featured",
    )
    limitations_disclaimer: str = Field(
        STANDARD_AI_DISCLAIMER,
        description="Mandatory disclaimer stating that automated analysis cannot rule out emergencies or diagnose illness",
    )


class PersonalizedEducationRequest(BaseModel):
    """Request for consented lifestyle guidance. Note: server verifies DB consent."""

    user_consent_given: bool = Field(
        False,
        description="Client consent assertion flag (server verifies database record for actual authorization).",
    )
    consent_terms_version: str | None = Field(
        None,
        description="Consent terms version acknowledged by client (e.g. '2026.1')",
    )
    survey_features: dict[str, Any] = Field(
        default_factory=dict,
        description="Survey lifestyle profile. The server verifies trusted DB consent and whitelists 25 CDC features.",
    )
    terms_version_acknowledged: str | None = Field(
        None,
        description="Consent terms version (e.g. '2026.1')",
    )
