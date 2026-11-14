"""HeartAI Generative AI API Routes — Aarogya Saathi (आरोग्य साथी).

Exposes secure, rate-limited REST endpoints for:
- Conversational cardiac education
- Vital metric explanations
- Model uncertainty and historical calibration explanations
- Deterministic emergency-screened symptom assessment
- Trusted database consent-gated personalized lifestyle guidance
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.ai.assistant import assistant
from app.ai.gemini_client import (
    GeminiAPIError,
    GeminiConfigError,
    GeminiRateLimitError,
    GeminiTimeoutError,
)
from app.api.deps import get_current_user, get_optional_current_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.models import User
from app.schemas.ai import (
    AIChatRequest,
    AIChatResponse,
    AIStatusResponse,
    MetricExplanationRequest,
    PersonalizedEducationRequest,
    RiskExplanationRequest,
    StructuredAIAdvice,
    SymptomAnalysisResponse,
    SymptomAssessmentInput,
)

logger = logging.getLogger("heartai.api.ai")

router = APIRouter(prefix="/ai", tags=["Generative AI Clinical Assistant"])


@router.get(
    "/status",
    response_model=AIStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check Gemini API Configuration and Readiness",
)
def get_ai_status(
    current_user: User | None = Depends(get_optional_current_user),
) -> AIStatusResponse:
    """Returns whether Gemini API credentials are configured and instructions if absent."""
    return assistant.get_status(current_user=current_user)


@router.post(
    "/chat",
    response_model=AIChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Healthcare Information Assistant Chat",
)
@limiter.limit(settings.RATE_LIMIT_AI_CHAT)
def chat_with_assistant(
    request: Request,
    payload: AIChatRequest,
    current_user: User | None = Depends(get_optional_current_user),
) -> AIChatResponse:
    """Answers patient questions regarding cardiovascular health with clinical safety guardrails."""
    try:
        return assistant.chat(payload, current_user=current_user)
    except GeminiRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The AI assistant is temporarily rate-limited. Please retry shortly.",
        ) from exc
    except GeminiTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The AI assistant response timed out. Please try again.",
        ) from exc
    except (GeminiConfigError, GeminiAPIError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI assistant is currently unavailable. Please verify API configuration.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error in /ai/chat")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the assistant response.",
        ) from exc


@router.post(
    "/symptoms",
    response_model=SymptomAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Symptom Assessment and Clinical Safety Guidance",
)
@limiter.limit(settings.RATE_LIMIT_AI_SYMPTOMS)
def assess_cardiovascular_symptoms(
    request: Request,
    payload: SymptomAssessmentInput,
) -> SymptomAnalysisResponse:
    """Performs deterministic emergency screening and conservative educational symptom assessment.

    Life-threatening warning signs trigger an immediate emergency alert (112 in India)
    before making any generative API calls.
    """
    try:
        return assistant.assess_symptoms(payload)
    except GeminiRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The symptom analysis service is temporarily busy. Please retry shortly.",
        ) from exc
    except GeminiTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The symptom analysis service response timed out. Please try again.",
        ) from exc
    except (GeminiConfigError, GeminiAPIError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The symptom assessment service is currently unavailable.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error in /ai/symptoms")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during symptom assessment.",
        ) from exc


@router.post(
    "/explain-metrics",
    response_model=AIChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Explain Vital Health Metric",
)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
def explain_metric(
    request: Request,
    payload: MetricExplanationRequest,
) -> AIChatResponse:
    """Explains physiological meaning and clinical ranges for a specific vital metric."""
    try:
        return assistant.explain_health_metric(payload)
    except Exception as exc:
        logger.exception("Error in /ai/explain-metrics")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate metric explanation.",
        ) from exc


@router.post(
    "/explain-risk",
    response_model=AIChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Explain Model Prediction Uncertainty and Survey Limitations",
)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
def explain_risk(
    request: Request,
    payload: RiskExplanationRequest,
) -> AIChatResponse:
    """Explains HeartAI prediction probability, calibration threshold, and survey limitations."""
    try:
        return assistant.explain_model_limitations(payload)
    except Exception as exc:
        logger.exception("Error in /ai/explain-risk")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate model limitations explanation.",
        ) from exc


@router.post(
    "/lifestyle",
    response_model=AIChatResponse,
    status_code=status.HTTP_200_OK,
    summary="General Cardiovascular Lifestyle Guidance",
)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
def get_lifestyle_education(
    request: Request,
    factors: list[str] | None = None,
) -> AIChatResponse:
    """Provides evidence-based lifestyle guidance aligned with AHA Life's Essential 8."""
    try:
        return assistant.generate_lifestyle_education(factors)
    except Exception as exc:
        logger.exception("Error in /ai/lifestyle")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate lifestyle education.",
        ) from exc


@router.post(
    "/personalized",
    response_model=AIChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Consented Personalized Lifestyle Guidance (Requires Authentication & DB Consent)",
)
@limiter.limit(settings.RATE_LIMIT_AI_PERSONALIZED)
def get_personalized_education(
    request: Request,
    payload: PersonalizedEducationRequest,
    current_user: User = Depends(get_current_user),
) -> AIChatResponse:
    """Provides lifestyle education tailored strictly to consented survey features.

    Requires an authenticated user session and verified server-side database consent.
    Client-supplied booleans are never trusted as proof of consent.
    """
    try:
        return assistant.generate_personalized_education(payload, current_user=current_user)
    except Exception as exc:
        logger.exception("Error in /ai/personalized")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate personalized guidance.",
        ) from exc


@router.post(
    "/structured-advice",
    response_model=StructuredAIAdvice,
    status_code=status.HTTP_200_OK,
    summary="Structured Educational Guidance Schema",
)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
def get_structured_advice(
    request: Request,
    topic: str = "Cardiovascular Prevention",
) -> StructuredAIAdvice:
    """Returns guaranteed schema-conforming structured cardiac education."""
    try:
        return assistant.generate_structured_advice(topic)
    except Exception as exc:
        logger.exception("Error in /ai/structured-advice")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate structured advice.",
        ) from exc
