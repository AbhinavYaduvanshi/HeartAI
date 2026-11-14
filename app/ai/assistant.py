"""HeartAI Clinical Generative AI Healthcare Assistant.

Orchestrates health education, metric interpretation, risk explanation,
lifestyle guidance, and medical safety guardrails using Google Gemini.
"""

from __future__ import annotations

import logging

from app.ai.gemini_client import (
    GeminiAPIError,
    GeminiConfigError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    gemini_client,
)
from app.ai.prompts import (
    SYSTEM_INSTRUCTION_HEALTHCARE_ASSISTANT,
    SYSTEM_INSTRUCTION_STRUCTURED_ADVICE,
    build_heart_health_education_prompt,
    build_lifestyle_education_prompt,
    build_metric_explanation_prompt,
    build_model_limitations_prompt,
    build_personalized_education_prompt,
)
from app.ai.safety import (
    detect_emergency_symptoms,
    sanitize_for_logging,
    sanitize_user_input,
    validate_and_guard_output,
)
from app.core.config import settings
from app.schemas.ai import (
    STANDARD_AI_DISCLAIMER,
    AIChatRequest,
    AIChatResponse,
    AIStatusResponse,
    MetricExplanationRequest,
    PersonalizedEducationRequest,
    RiskExplanationRequest,
    StructuredAIAdvice,
)

logger = logging.getLogger("heartai.ai.assistant")


class HeartAIAssistant:
    """High-level cardiovascular clinical education assistant."""

    def __init__(self) -> None:
        self.client = gemini_client

    def get_status(self) -> AIStatusResponse:
        """Returns the readiness and configuration status of the Gemini AI integration."""
        is_ready = self.client.is_available()
        msg = (
            f"Google Gemini AI is active and configured using model '{settings.GEMINI_MODEL}'."
            if is_ready
            else (
                "Google Gemini AI is currently unconfigured or using a placeholder key. "
                "To enable live AI features, obtain a free API key at https://aistudio.google.com/ "
                "and set GEMINI_API_KEY in your .env configuration."
            )
        )
        return AIStatusResponse(
            configured=is_ready,
            model=settings.GEMINI_MODEL,
            message=msg,
        )

    def chat(self, request: AIChatRequest) -> AIChatResponse:
        """Handles conversational health queries with safety checks and emergency screening."""
        clean_prompt = sanitize_user_input(request.message)
        logger.info(
            "AI Assistant processing query (length: %d chars, consent: %s)",
            len(clean_prompt),
            request.user_consent_given,
        )

        # 1. Immediate Acute Emergency Symptom Screening
        is_emergency, emergency_msg = detect_emergency_symptoms(clean_prompt)

        # 2. Check if API is configured
        if not self.client.is_available():
            fallback_text = (
                "HeartAI Gemini Assistant is ready for integration, but a valid Google AI Studio "
                "API key is not yet configured in this environment.\n\n"
                f"{self.client.get_auth_instructions()}"
            )
            if is_emergency:
                fallback_text = f"{emergency_msg}\n\n---\n{fallback_text}"

            return AIChatResponse(
                response_text=fallback_text,
                emergency_flag=is_emergency,
                emergency_guidance=emergency_msg,
                model_used="unconfigured-placeholder",
                disclaimer=STANDARD_AI_DISCLAIMER,
            )

        # 3. Generate response via Gemini
        try:
            raw_response = self.client.generate_text(
                prompt=clean_prompt,
                system_instruction=SYSTEM_INSTRUCTION_HEALTHCARE_ASSISTANT,
            )
            safe_text = validate_and_guard_output(raw_response)

            if is_emergency and emergency_msg:
                safe_text = f"{emergency_msg}\n\n---\n{safe_text}"

            return AIChatResponse(
                response_text=safe_text,
                emergency_flag=is_emergency,
                emergency_guidance=emergency_msg,
                model_used=settings.GEMINI_MODEL,
                disclaimer=STANDARD_AI_DISCLAIMER,
            )
        except (GeminiRateLimitError, GeminiTimeoutError, GeminiAPIError, GeminiConfigError) as err:
            logger.warning("AI Assistant generation error: %s", err)
            error_response = (
                f"HeartAI Assistant encountered a temporary service condition: {err}\n\n"
                "Please retry in a moment. If symptoms are severe, seek medical care immediately."
            )
            if is_emergency and emergency_msg:
                error_response = f"{emergency_msg}\n\n---\n{error_response}"

            return AIChatResponse(
                response_text=error_response,
                emergency_flag=is_emergency,
                emergency_guidance=emergency_msg,
                model_used=settings.GEMINI_MODEL,
                disclaimer=STANDARD_AI_DISCLAIMER,
            )

    def explain_heart_health(self, topic: str) -> AIChatResponse:
        """Generates general heart-health education on a given topic."""
        clean_topic = sanitize_user_input(topic)
        prompt = build_heart_health_education_prompt(clean_topic)
        return self.chat(AIChatRequest(message=prompt, user_consent_given=False))

    def explain_health_metric(self, request: MetricExplanationRequest) -> AIChatResponse:
        """Explains physiological meaning and guidelines for a vital metric."""
        clean_name = sanitize_user_input(request.metric_name)
        prompt = build_metric_explanation_prompt(
            metric_name=clean_name,
            metric_value=request.metric_value,
            unit=request.unit,
        )
        return self.chat(AIChatRequest(message=prompt, user_consent_given=False))

    def explain_model_limitations(self, request: RiskExplanationRequest) -> AIChatResponse:
        """Explains HeartAI prediction uncertainty, screening threshold, and CDC BRFSS limitations."""
        prompt = build_model_limitations_prompt(
            estimated_probability=request.estimated_probability,
            binary_classification=request.binary_classification,
            operating_threshold=request.operating_threshold,
        )
        return self.chat(AIChatRequest(message=prompt, user_consent_given=request.user_consent_given))

    def generate_lifestyle_education(
        self,
        lifestyle_factors: list[str] | None = None,
    ) -> AIChatResponse:
        """Generates evidence-based lifestyle guidance aligned with AHA Life's Essential 8."""
        prompt = build_lifestyle_education_prompt(lifestyle_factors)
        return self.chat(AIChatRequest(message=prompt, user_consent_given=False))

    def generate_personalized_education(
        self,
        request: PersonalizedEducationRequest,
    ) -> AIChatResponse:
        """Generates consented educational lifestyle guidance, strictly respecting user consent."""
        sanitized_features = sanitize_for_logging(request.survey_features)
        prompt = build_personalized_education_prompt(
            survey_features=sanitized_features,
            user_consent_given=request.user_consent_given,
        )
        return self.chat(AIChatRequest(message=prompt, user_consent_given=request.user_consent_given))

    def generate_structured_advice(self, topic: str) -> StructuredAIAdvice:
        """Generates structured educational advice conforming to Pydantic schema."""
        clean_topic = sanitize_user_input(topic)
        if not self.client.is_available():
            return StructuredAIAdvice(
                title=f"Education on {clean_topic}",
                summary="Gemini AI is ready for integration once Google AI Studio credentials are configured.",
                key_points=[
                    "Heart health is enhanced by regular cardiovascular physical activity (150 mins/week).",
                    "A Mediterranean or DASH dietary pattern supports endothelial wellness.",
                    "Routine blood pressure and lipid monitoring aid early detection of risk patterns.",
                ],
                lifestyle_recommendations=[
                    "Engage in moderate-intensity aerobic exercise regularly.",
                    "Maintain dietary sodium below recommended clinical limits.",
                    "Target 7-9 hours of restorative sleep nightly.",
                ],
                questions_for_doctor=[
                    "What are my personal target ranges for blood pressure and lipid levels?",
                    "Are there any specific lifestyle modifications recommended for my health history?",
                ],
                disclaimer=STANDARD_AI_DISCLAIMER,
            )

        try:
            return self.client.generate_structured(
                prompt=f"Provide structured cardiovascular guidance for: {clean_topic}",
                response_model=StructuredAIAdvice,
                system_instruction=SYSTEM_INSTRUCTION_STRUCTURED_ADVICE,
            )
        except Exception as exc:
            logger.warning("Structured generation fallback triggered: %s", exc)
            return StructuredAIAdvice(
                title=f"Heart Health: {clean_topic}",
                summary=f"Educational overview of {clean_topic} regarding cardiovascular physiology.",
                key_points=[
                    "Cardiovascular wellness relies on maintaining optimal hemodynamics.",
                    "Lifestyle factors significantly influence arterial elasticity and heart rate variability.",
                ],
                lifestyle_recommendations=[
                    "Incorporate regular moderate cardiovascular activity.",
                    "Eat a balanced diet rich in whole grains, vegetables, and lean proteins.",
                ],
                questions_for_doctor=["How does this topic relate to my overall cardiac profile?"],
                disclaimer=STANDARD_AI_DISCLAIMER,
            )


assistant = HeartAIAssistant()
