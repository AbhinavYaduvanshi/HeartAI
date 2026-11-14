"""HeartAI Clinical Generative AI Healthcare Assistant — Aarogya Saathi (आरोग्य साथी).

Orchestrates health education, metric interpretation, symptom analysis,
CDC BRFSS historical model limitations, and trusted consent-gated personalization.
"""

from __future__ import annotations

import logging
import re

from app.ai.gemini_client import (
    gemini_client,
)
from app.ai.prompts import (
    SYSTEM_INSTRUCTION_AAROGYA_SAATHI,
    SYSTEM_INSTRUCTION_STRUCTURED_ADVICE,
    SYSTEM_INSTRUCTION_SYMPTOM_ANALYSIS,
    build_future_risk_explanation,
    build_heart_health_education_prompt,
    build_lifestyle_education_prompt,
    build_metric_explanation_prompt,
    build_model_limitations_prompt,
    build_personalized_education_prompt,
    build_symptom_analysis_prompt,
)
from app.ai.safety import (
    OUT_OF_DOMAIN_RESPONSE,
    detect_emergency_symptoms,
    sanitize_user_input,
    validate_and_guard_output,
    validate_heartai_domain,
)
from app.core.config import settings
from app.db.models import User
from app.schemas.ai import (
    EMERGENCY_CONTACT_NUMBERS,
    STANDARD_AI_DISCLAIMER,
    AIChatRequest,
    AIChatResponse,
    AIStatusResponse,
    MetricExplanationRequest,
    PersonalizedEducationRequest,
    RiskExplanationRequest,
    StructuredAIAdvice,
    SymptomAnalysisResponse,
    SymptomAssessmentInput,
    SymptomSeverity,
    SymptomUrgencyCategory,
)
from app.services.consent_service import (
    filter_approved_survey_features,
    verify_trusted_user_consent,
)

logger = logging.getLogger("heartai.ai.assistant")

FUTURE_RISK_PATTERNS = [
    r"\b(will\s+i\s+have\s+a\s+heart\s+attack|am\s+i\s+going\s+to\s+have\s+a\s+heart\s+attack)\b",
    r"\b(predict\s+(my\s+)?(future\s+)?(risk|heart\s+attack|cardiac\s+event))\b",
    r"\b(what\s+is\s+my\s+future\s+(risk|chance))\b",
    r"\b(future\s+(heart\s+attack|cardiac\s+event|risk))\b",
    r"\b(when\s+will\s+i\s+have\s+a\s+heart\s+attack)\b",
    r"\b(chance\s+of\s+(a\s+)?(future\s+)?(heart\s+attack|cardiac\s+event))\b",
]


class HeartAIAssistant:
    """Aarogya Saathi (आरोग्य साथी) — HeartAI Healthcare Education Companion."""

    def __init__(self) -> None:
        self.client = gemini_client
        self.name = "Aarogya Saathi (आरोग्य साथी)"

    def get_status(self, current_user: User | None = None) -> AIStatusResponse:
        """Returns readiness and configuration status without triggering paid API calls."""
        is_ready = self.client.is_available()
        msg = (
            f"{self.name} is online and operational using model '{settings.GEMINI_MODEL}'."
            if is_ready
            else (
                f"{self.name} is ready for integration, but a valid Google AI Studio "
                "API key is not configured in this environment. "
                "Add your GEMINI_API_KEY to .env to enable live generation."
            )
        )
        return AIStatusResponse(
            configured=is_ready,
            model=settings.GEMINI_MODEL,
            assistant_name=self.name,
            authenticated_client=current_user is not None,
            message=msg,
        )

    def chat(self, request: AIChatRequest, current_user: User | None = None) -> AIChatResponse:
        """Processes inquiries with strict HeartAI domain validation and emergency screening."""
        clean_prompt = sanitize_user_input(request.message)

        # 1. Immediate Acute Emergency Symptom Screening (BEFORE GEMINI)
        is_emergency, emergency_msg = detect_emergency_symptoms(clean_prompt)
        if is_emergency and emergency_msg:
            # Immediate return without waiting for or calling Gemini
            return AIChatResponse(
                response_text=emergency_msg,
                assistant_name=self.name,
                emergency_flag=True,
                emergency_guidance=emergency_msg,
                domain_restricted=False,
                model_used="emergency-guard-pre-gemini",
                disclaimer=STANDARD_AI_DISCLAIMER,
            )

        # 2. Strict HeartAI-Only Domain Enforcement (BEFORE GEMINI)
        in_domain, domain_rejection = validate_heartai_domain(clean_prompt)
        if not in_domain:
            return AIChatResponse(
                response_text=domain_rejection or OUT_OF_DOMAIN_RESPONSE,
                assistant_name=self.name,
                emergency_flag=False,
                emergency_guidance=None,
                domain_restricted=True,
                model_used="domain-guard-pre-gemini",
                disclaimer=STANDARD_AI_DISCLAIMER,
            )

        # 3. Check for Out-of-Scope Future Heart Attack Predictions
        lowered_prompt = clean_prompt.lower()
        if request.feature_context != "analytics" and any(re.search(pat, lowered_prompt) for pat in FUTURE_RISK_PATTERNS):
            return AIChatResponse(
                response_text=build_future_risk_explanation(),
                assistant_name=self.name,
                emergency_flag=False,
                emergency_guidance=None,
                domain_restricted=False,
                model_used="future-risk-guard",
                disclaimer=STANDARD_AI_DISCLAIMER,
            )

        # 4. Check if Google Gemini API Credentials are Ready
        if not self.client.is_available():
            fallback_text = (
                f"I'm {self.name}, your HeartAI health education companion. "
                "Live generative responses require an active Google AI Studio API key.\n\n"
                f"{self.client.get_auth_instructions()}"
            )
            return AIChatResponse(
                response_text=fallback_text,
                assistant_name=self.name,
                emergency_flag=False,
                emergency_guidance=None,
                domain_restricted=False,
                model_used="unconfigured-placeholder",
                disclaimer=STANDARD_AI_DISCLAIMER,
            )

        # 5. Build Bounded Context with Feature Awareness
        constructed_prompt = clean_prompt
        if request.feature_context:
            context_summary = f"[Active HeartAI Feature: {request.feature_context}]"
            if request.context_data and isinstance(request.context_data, dict):
                safe_ctx = {
                    k: v for k, v in request.context_data.items()
                    if k in {"metric_name", "value", "probability", "threshold", "classification", "topic"}
                }
                if safe_ctx:
                    context_summary += f" Context: {safe_ctx}"
            constructed_prompt = f"{context_summary}\n\nUser Question: {clean_prompt}"

        # Append sanitized conversation history (max 6 turns, user/assistant only)
        if request.conversation_history:
            history_lines = []
            for turn in request.conversation_history[-6:]:
                role_label = "User" if turn.role == "user" else "Assistant"
                sanitized_text = sanitize_user_input(turn.text)
                history_lines.append(f"{role_label}: {sanitized_text}")
            constructed_prompt = "\n".join(history_lines) + f"\nUser: {clean_prompt}"

        # 6. Generate Educational Response via Gemini
        raw_response = self.client.generate_text(
            prompt=constructed_prompt,
            system_instruction=SYSTEM_INSTRUCTION_AAROGYA_SAATHI,
        )
        safe_text = validate_and_guard_output(raw_response)

        return AIChatResponse(
            response_text=safe_text,
            assistant_name=self.name,
            emergency_flag=False,
            emergency_guidance=None,
            domain_restricted=False,
            model_used=settings.GEMINI_MODEL,
            disclaimer=STANDARD_AI_DISCLAIMER,
        )

    def assess_symptoms(self, symptom_input: SymptomAssessmentInput) -> SymptomAnalysisResponse:
        """Performs non-diagnostic cardiovascular symptom urgency assessment.

        Enforces emergency detection BEFORE any Gemini API call.
        """
        combined_text = (
            f"{symptom_input.symptoms_experienced} "
            f"{' '.join(symptom_input.associated_symptoms)}"
        )
        clean_text = sanitize_user_input(combined_text)

        # 1. Deterministic Emergency Detection BEFORE GEMINI
        is_emergency, emergency_msg = detect_emergency_symptoms(clean_text)
        is_severe = symptom_input.severity == SymptomSeverity.SEVERE
        has_chest_pattern = any(
            w in clean_text.lower() for w in ["chest", "breathe", "breathing", "radiat", "faint", "syncope"]
        )

        if is_emergency or (is_severe and has_chest_pattern):
            # Immediate return without waiting for or calling Gemini
            return SymptomAnalysisResponse(
                symptom_summary=f"Reported symptoms: {symptom_input.symptoms_experienced} (Onset: {symptom_input.onset_time}, Severity: {symptom_input.severity.value})",
                general_cardiovascular_relevance="The reported symptom constellation indicates potential acute cardiovascular compromise or ischemia requiring immediate physical clinical evaluation.",
                warning_signs_identified=[
                    "Potentially life-threatening acute cardiovascular symptoms detected",
                    f"Onset: {symptom_input.onset_time}",
                    f"Reported severity: {symptom_input.severity.value}",
                ],
                urgency_category=SymptomUrgencyCategory.EMERGENCY,
                suggested_next_action="CALL EMERGENCY SERVICES IMMEDIATELY (112 in India, 911 in US/Canada, 999 in UK). Do not wait and do not attempt to drive yourself.",
                is_emergency=True,
                emergency_contacts=EMERGENCY_CONTACT_NUMBERS,
                limitations_disclaimer=STANDARD_AI_DISCLAIMER,
            )

        # 2. Check if API is Configured
        if not self.client.is_available():
            return SymptomAnalysisResponse(
                symptom_summary=f"Reported symptoms: {symptom_input.symptoms_experienced} (Onset: {symptom_input.onset_time}, Severity: {symptom_input.severity.value})",
                general_cardiovascular_relevance="Cardiovascular symptoms can stem from arterial, electrical, or structural heart changes, or non-cardiac causes such as muscular or gastrointestinal issues.",
                warning_signs_identified=[
                    "Automated live AI is awaiting Google AI Studio credentials",
                    f"Progression: {symptom_input.progression.value}",
                ],
                urgency_category=SymptomUrgencyCategory.URGENT if is_severe else SymptomUrgencyCategory.ROUTINE,
                suggested_next_action="Schedule an evaluation with your primary physician or cardiologist for a formal physical exam and diagnostic workup.",
                is_emergency=False,
                emergency_contacts=EMERGENCY_CONTACT_NUMBERS,
                limitations_disclaimer=STANDARD_AI_DISCLAIMER,
            )

        # 3. Generate Structured Symptom Guidance via Gemini
        prompt = build_symptom_analysis_prompt(symptom_input)
        try:
            structured_res = self.client.generate_structured(
                prompt=prompt,
                response_model=SymptomAnalysisResponse,
                system_instruction=SYSTEM_INSTRUCTION_SYMPTOM_ANALYSIS,
            )
            # Guard output against inadvertent diagnostic claims
            structured_res.general_cardiovascular_relevance = validate_and_guard_output(
                structured_res.general_cardiovascular_relevance
            )
            return structured_res
        except Exception as exc:
            logger.warning("Structured symptom assessment fallback triggered: %s", exc)
            return SymptomAnalysisResponse(
                symptom_summary=f"Reported symptoms: {symptom_input.symptoms_experienced} (Severity: {symptom_input.severity.value})",
                general_cardiovascular_relevance="Cardiovascular symptoms warrant clinical correlation. Physical symptoms can stem from vascular, muscular, metabolic, or psychological factors.",
                warning_signs_identified=["Symptom onset reported: " + symptom_input.onset_time],
                urgency_category=SymptomUrgencyCategory.URGENT if is_severe else SymptomUrgencyCategory.ROUTINE,
                suggested_next_action="Consult a qualified healthcare provider for clinical evaluation.",
                is_emergency=False,
                emergency_contacts=EMERGENCY_CONTACT_NUMBERS,
                limitations_disclaimer=STANDARD_AI_DISCLAIMER,
            )

    def explain_heart_health(self, topic: str) -> AIChatResponse:
        """Generates general heart-health education on a given topic."""
        clean_topic = sanitize_user_input(topic)
        prompt = build_heart_health_education_prompt(clean_topic)
        return self.chat(AIChatRequest(message=prompt, feature_context="education"))

    def explain_health_metric(self, request: MetricExplanationRequest) -> AIChatResponse:
        """Explains physiological meaning and guidelines for a vital metric."""
        clean_name = sanitize_user_input(request.metric_name)
        prompt = build_metric_explanation_prompt(
            metric_name=clean_name,
            metric_value=request.metric_value,
            unit=request.unit,
        )
        return self.chat(AIChatRequest(message=prompt, feature_context="metrics"))

    def explain_model_limitations(self, request: RiskExplanationRequest) -> AIChatResponse:
        """Explains HeartAI prediction uncertainty, screening threshold, and CDC BRFSS limitations."""
        prompt = build_model_limitations_prompt(
            estimated_probability=request.estimated_probability,
            binary_classification=request.binary_classification,
            operating_threshold=request.operating_threshold,
            feature_context=request.feature_context,
        )
        return self.chat(AIChatRequest(message=prompt, feature_context="analytics"))

    def generate_lifestyle_education(
        self,
        lifestyle_factors: list[str] | None = None,
    ) -> AIChatResponse:
        """Generates evidence-based lifestyle guidance aligned with AHA Life's Essential 8."""
        prompt = build_lifestyle_education_prompt(lifestyle_factors)
        return self.chat(AIChatRequest(message=prompt, feature_context="lifestyle"))

    def generate_personalized_education(
        self,
        request: PersonalizedEducationRequest,
        current_user: User | None = None,
    ) -> AIChatResponse:
        """Generates consented educational lifestyle guidance using verified server-side consent."""
        if current_user is not None:
            # Enforce Trusted Server-Side Consent Verification (Point 8.1)
            is_consent_verified, reason = verify_trusted_user_consent(current_user)
        else:
            # Standalone / test fallback: verify explicit test consent fields
            terms_ver = request.consent_terms_version or request.terms_version_acknowledged
            if request.user_consent_given and terms_ver == settings.CURRENT_CONSENT_TERMS_VERSION:
                is_consent_verified = True
                reason = "Consent verified"
            else:
                is_consent_verified = False
                reason = "Affirmative informed consent is required to personalize health education with individual survey indicators."

        # Strictly whitelist 25 CDC features and strip any unexpected keys
        sanitized_features = filter_approved_survey_features(request.survey_features)

        if not is_consent_verified:
            logger.info("Personalized AI education consent unverified: %s. Falling back to general guidance.", reason)
            prompt = build_personalized_education_prompt(
                survey_features={},
                user_consent_verified=False,
            )
            fallback_resp = self.chat(AIChatRequest(message=prompt, feature_context="personalized"))
            fallback_resp.response_text = (
                f"**Notice**: {reason}\n\n"
                f"{fallback_resp.response_text}"
            )
            return fallback_resp

        prompt = build_personalized_education_prompt(
            survey_features=sanitized_features,
            user_consent_verified=True,
        )
        return self.chat(AIChatRequest(message=prompt, feature_context="personalized"))

    def generate_structured_advice(self, topic: str) -> StructuredAIAdvice:
        """Generates structured educational advice conforming to Pydantic schema."""
        clean_topic = sanitize_user_input(topic)
        if not self.client.is_available():
            return StructuredAIAdvice(
                title=f"Education on {clean_topic}",
                summary="Aarogya Saathi is ready for integration once Google AI Studio credentials are configured.",
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
