"""HeartAI Generative AI API Routes.

Exposes REST endpoints for conversational cardiac education, metric explanation,
prediction uncertainty breakdown, and consented personalized lifestyle guidance.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.ai.assistant import assistant
from app.schemas.ai import (
    AIChatRequest,
    AIChatResponse,
    AIStatusResponse,
    MetricExplanationRequest,
    PersonalizedEducationRequest,
    RiskExplanationRequest,
    StructuredAIAdvice,
)

router = APIRouter(prefix="/ai", tags=["Generative AI Clinical Assistant"])


@router.get(
    "/status",
    response_model=AIStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check Gemini API Configuration and Readiness",
)
def get_ai_status() -> AIStatusResponse:
    """Returns whether Gemini API credentials are configured and instructions if absent."""
    return assistant.get_status()


@router.post(
    "/chat",
    response_model=AIChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Healthcare Information Assistant Chat",
)
def chat_with_assistant(request: AIChatRequest) -> AIChatResponse:
    """Answers patient questions regarding cardiovascular health with clinical safety guardrails."""
    return assistant.chat(request)


@router.post(
    "/explain-metrics",
    response_model=AIChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Explain Vital Health Metric",
)
def explain_metric(request: MetricExplanationRequest) -> AIChatResponse:
    """Explains physiological meaning and clinical ranges for a specific vital metric."""
    return assistant.explain_health_metric(request)


@router.post(
    "/explain-risk",
    response_model=AIChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Explain Model Prediction Uncertainty and Survey Limitations",
)
def explain_risk(request: RiskExplanationRequest) -> AIChatResponse:
    """Explains HeartAI prediction probability, calibration threshold, and survey limitations."""
    return assistant.explain_model_limitations(request)


@router.post(
    "/lifestyle",
    response_model=AIChatResponse,
    status_code=status.HTTP_200_OK,
    summary="General Cardiovascular Lifestyle Guidance",
)
def get_lifestyle_education(factors: list[str] | None = None) -> AIChatResponse:
    """Provides evidence-based lifestyle guidance aligned with AHA Life's Essential 8."""
    return assistant.generate_lifestyle_education(factors)


@router.post(
    "/personalized",
    response_model=AIChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Consented Personalized Lifestyle Guidance",
)
def get_personalized_education(request: PersonalizedEducationRequest) -> AIChatResponse:
    """Provides lifestyle education tailored strictly to consented survey features."""
    return assistant.generate_personalized_education(request)


@router.post(
    "/structured-advice",
    response_model=StructuredAIAdvice,
    status_code=status.HTTP_200_OK,
    summary="Structured Educational Guidance Schema",
)
def get_structured_advice(topic: str = "Cardiovascular Prevention") -> StructuredAIAdvice:
    """Returns guaranteed schema-conforming structured cardiac education."""
    return assistant.generate_structured_advice(topic)
