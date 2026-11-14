"""HeartAI Generative AI Medical Safety and Privacy Guardrails — Aarogya Saathi.

Enforces clinical safety restrictions, strict HeartAI-only domain validation,
adversarial prompt-injection prevention, emergency symptom detection,
PII scrubbing, log anonymization, and mandatory educational disclaimers.
"""

from __future__ import annotations

import re
from typing import Any

from google.genai import types

from app.schemas.ai import EMERGENCY_CONTACT_NUMBERS, STANDARD_AI_DISCLAIMER

# Standard out-of-domain rejection response required by HeartAI specifications
OUT_OF_DOMAIN_RESPONSE = (
    "I'm Aarogya Saathi, HeartAI's health assistant. I can help with HeartAI, heart health, "
    "cardiovascular symptoms, health metrics, and understanding your assessment results. "
    "I cannot assist with unrelated topics."
)

# Prominently features India (112) with guidance to use local emergency numbers
EMERGENCY_ALERT_MESSAGE = (
    "🚨 CRITICAL HEALTH ALERT: The symptoms described may indicate an acute cardiovascular "
    "or neurological emergency (such as a heart attack or acute stroke). "
    "DO NOT WAIT. Call emergency services immediately:\n"
    f"• India: {EMERGENCY_CONTACT_NUMBERS['India']}\n"
    f"• US / Canada: {EMERGENCY_CONTACT_NUMBERS['US / Canada']}\n"
    f"• United Kingdom: {EMERGENCY_CONTACT_NUMBERS['United Kingdom']}\n"
    f"• Europe: {EMERGENCY_CONTACT_NUMBERS['Europe']}\n"
    "Or contact your local emergency response service right away. "
    "While waiting for assistance: sit or lie down comfortably, stay calm, and do not attempt to drive yourself."
)

# Acute emergency trigger patterns requiring immediate emergency guidance
EMERGENCY_KEYWORDS = [
    r"\bcrushing\s+chest\s+pain\b",
    r"\bchest\s+tightness\b",
    r"\bpressure\s+in\s+(my\s+)?chest\b",
    r"\bheavy\s+(weight|pressure|heaviness)\s+(on|in)\s+(my\s+)?chest\b",
    r"\belephant\s+sitting\s+on\s+(my\s+)?chest\b",
    r"\bsevere\s+squeezing\s+(in|of)\s+(my\s+)?chest\b",
    r"\b(suffocation|suffocating)\s+(in|around)\s+(my\s+)?chest\b",
    r"\bchest\s+suffocation\b",
    r"\bpain\s+(radiating|spreading)\s+to\s+(my\s+)?(left\s+)?(arm|jaw|neck|back|shoulder)\b",
    r"\bburning\s+in\s+(my\s+)?chest\s+(radiating|spreading)\s+to\s+(my\s+)?(left\s+)?(arm|jaw|neck|back|shoulder)\b",
    r"\bcold\s+sweats?\s+(with|and)\s+chest\s+pain\b",
    r"\bchest\s+pain\s+(with|and)\s+cold\s+sweats?\b",
    r"\bsevere\s+(shortness\s+of\s+breath|difficulty\s+breathing)\b",
    r"\bgasping\s+for\s+(air|breath)\b",
    r"\bcan'?t\s+breathe\b",
    r"\bsudden\s+(numbness|weakness|paralysis)\b",
    r"\bslurred\s+speech\b",
    r"\bfacial\s+droop\b",
    r"\bsudden\s+loss\s+of\s+consciousness\b",
    r"\bpassed\s+out\b",
    r"\bcollapsed\b",
    r"\bfainted\b",
    r"\bsyncope\b",
]

# Prompt-injection, jailbreak, and adversarial role-play patterns
PROMPT_INJECTION_PATTERNS = [
    r"\b(ignore|disregard|forget)\s+(all\s+|your\s+|previous\s+)?(instructions?|prompts?|rules?)\b",
    r"\b(system\s+prompt|reveal\s+your\s+prompt|print\s+your\s+instructions)\b",
    r"\b(jailbreak|dan\s+mode|developer\s+mode|unfiltered\s+mode)\b",
    r"\b(you\s+are\s+now|pretend\s+you\s+are|roleplay\s+as|act\s+as)\s+(a\s+)?(hacker|python|coder|terminal|politician|gamer|unrestricted)\b",
    r"\b(bypass\s+safety|disable\s+guardrails?|ignore\s+domain)\b",
]

# Disallowed topics completely unrelated to HeartAI or cardiology
DISALLOWED_TOPIC_PATTERNS = [
    r"\b(write\s+a?\s*(python|javascript|c\+\+|java|rust|sql|html)\s+(script|code|program|function))\b",
    r"\b(solve\s+this\s+(math|algebra|calculus|equation|homework|physics))\b",
    r"\b(who\s+won\s+the\s+(election|match|game|super\s+bowl|world\s+cup))\b",
    r"\b(politics|political\s+party|president|prime\s+minister|democrat|republican|bjp|congress)\b",
    r"\b(movie\s+recommendations?|celebrity\s+gossip|actor|actress|hollywood|bollywood)\b",
    r"\b(buy\s+(bitcoin|crypto|stocks|shares)|stock\s+market\s+prediction|forex)\b",
    r"\b(write\s+an?\s*(essay|poem|song|story|joke))\b",
]

# Whitelist indicators for legitimate HeartAI and cardiovascular wellness topics
ALLOWED_DOMAIN_PATTERNS = [
    r"\b(heartai|heart|cardiac|cardio|cardiovascular|cardiology|cardiologist)\b",
    r"\b(blood\s+pressure|bp|hypertension|hypotension|systolic|diastolic|mmhg)\b",
    r"\b(cholesterol|ldl|hdl|triglycerides?|lipids?)\b",
    r"\b(ecg|ekg|rhythm|arrhythmia|fibrillation|palpitations?|tachycardia|bradycardia)\b",
    r"\b(pulse|heart\s+rate|bpm|hrv|heart\s+rate\s+variability|spo2|oxygen\s+saturation)\b",
    r"\b(chest\s+pain|angina|myocardial|infarction|ischemia|artery|atherosclerosis|stroke)\b",
    r"\b(bmi|body\s+mass\s+index|obesity|weight|overweight)\b",
    r"\b(smoking|smoker|nicotine|tobacco|alcohol|drinking)\b",
    r"\b(physical\s+activity|exercise|aerobic|walking|dash\s+diet|mediterranean\s+diet|sodium|salt)\b",
    r"\b(life'?s\s+essential\s+8|aha|american\s+heart\s+association|sleep\s+hygiene)\b",
    r"\b(symptoms?|breathlessness|shortness\s+of\s+breath|dyspnea|edema|swelling|dizziness)\b",
    r"\b(model|prediction|probability|threshold|0\.09|calibration|screening|brfss|cdc|accuracy|sensitivity|specificity)\b",
    r"\b(aarogya\s+saathi|assistant|features?|analytics|assessment|survey)\b",
]

# Prohibited clinical diagnosis, prescription, and future-prediction patterns
DISALLOWED_MEDICAL_PATTERNS = [
    (r"\b(i\s+diagnose\s+you\s+with|you\s+have\s+been\s+diagnosed\s+with|you\s+definitely\s+have)\b", "diagnosis"),
    (r"\b(stop\s+taking\s+(your\s+)?(medication|medicine|prescriptions?)|discontinue\s+your\s+pills?|change\s+your\s+dose)\b", "medication_alteration"),
    (r"\b(take\s+\d+\s*(mg|milligrams?|tablets?)|prescribe\s+[a-z]+)\b", "prescription"),
    (r"\b(this\s+prediction\s+is\s+medically\s+verified|confirmed\s+by\s+doctor|proves\s+you\s+have)\b", "verification_claim"),
    (r"\b(you\s+(will|are\s+going\s+to)\s+suffer\s+a\s+heart\s+attack|future\s+heart\s+attack\s+risk\s+is\s+\d+)\b", "future_event_claim"),
]

# PII Regex patterns for input scrubbing
PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]"),
    (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "[REDACTED_CARD]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[REDACTED_EMAIL]"),
    (r"\b(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b", "[REDACTED_PHONE]"),
]


def validate_heartai_domain(text: str) -> tuple[bool, str | None]:
    """Validates that a user request belongs strictly to the HeartAI cardiovascular domain.

    Returns:
        (True, None) if the request is legitimate and relevant.
        (False, OUT_OF_DOMAIN_RESPONSE) if unrelated, adversarial, or out of scope.
    """
    if not text or len(text.strip()) < 2:
        return False, OUT_OF_DOMAIN_RESPONSE

    lowered = text.lower().strip()

    # 1. Reject Prompt Injection / Roleplay Hijacking
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return False, OUT_OF_DOMAIN_RESPONSE

    # 2. Reject Explicitly Disallowed Topics (Programming, politics, entertainment, etc.)
    for pattern in DISALLOWED_TOPIC_PATTERNS:
        if re.search(pattern, lowered):
            return False, OUT_OF_DOMAIN_RESPONSE

    # 3. Check for Actual HeartAI & Cardiovascular Relevance
    has_relevant_topic = any(re.search(pat, lowered) for pat in ALLOWED_DOMAIN_PATTERNS)
    if not has_relevant_topic:
        return False, OUT_OF_DOMAIN_RESPONSE

    return True, None


def detect_emergency_symptoms(text: str) -> tuple[bool, str | None]:
    """Scans text for acute emergency cardiovascular or neurological symptoms.

    Executes deterministically BEFORE any Gemini API call.
    Returns:
        (True, EMERGENCY_ALERT_MESSAGE) if potential emergency indicators found.
        (False, None) otherwise.
    """
    if not text:
        return False, None

    lowered = text.lower()
    for pattern in EMERGENCY_KEYWORDS:
        if re.search(pattern, lowered):
            return True, EMERGENCY_ALERT_MESSAGE
    return False, None


def sanitize_user_input(text: str) -> str:
    """Scrubs sensitive Personally Identifiable Information (PII) from user prompts."""
    if not text:
        return ""
    sanitized = text
    for pattern, replacement in PII_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized.strip()


def sanitize_for_logging(data: Any) -> Any:
    """Masks clinical values and PII before writing to application log files."""
    if isinstance(data, dict):
        masked: dict[str, Any] = {}
        for k, v in data.items():
            k_low = k.lower()
            if (
                k_low in {"password", "secret", "secret_key", "token", "api_key", "gemini_api_key"}
                or "secret" in k_low
                or "password" in k_low
                or "token" in k_low
            ):
                masked[k] = "[REDACTED_SECRET]"
            elif k_low in {"email", "phone", "name", "address"}:
                masked[k] = "[REDACTED_PII]"
            elif isinstance(v, (dict, list)):
                masked[k] = sanitize_for_logging(v)
            else:
                masked[k] = v
        return masked
    elif isinstance(data, list):
        return [sanitize_for_logging(item) for item in data]
    elif isinstance(data, str):
        return sanitize_user_input(data)
    return data


def validate_and_guard_output(model_output: str) -> str:
    """Ensures model output contains no prohibited diagnostic, prescriptive, or future-prediction claims.

    If prohibited statements are detected, replaces them with safe educational disclaimers.
    """
    if not model_output:
        return STANDARD_AI_DISCLAIMER

    guarded = model_output
    lowered = guarded.lower()

    for pattern, rule_type in DISALLOWED_MEDICAL_PATTERNS:
        if re.search(pattern, lowered):
            if rule_type == "diagnosis":
                guarded = re.sub(
                    pattern,
                    "HeartAI cannot diagnose medical conditions, but clinical research indicates that",
                    guarded,
                    flags=re.IGNORECASE,
                )
            elif rule_type in {"medication_alteration", "prescription"}:
                guarded = re.sub(
                    pattern,
                    "Never start, stop, or alter any medication without direct evaluation by your prescribing physician or doctor",
                    guarded,
                    flags=re.IGNORECASE,
                )
            elif rule_type == "verification_claim":
                guarded = re.sub(
                    pattern,
                    "This educational estimate reflects historical population statistics and is not clinical verification",
                    guarded,
                    flags=re.IGNORECASE,
                )
            elif rule_type == "future_event_claim":
                guarded = re.sub(
                    pattern,
                    "HeartAI's model estimates historical self-reported CVD pattern association and does not predict future acute heart attacks",
                    guarded,
                    flags=re.IGNORECASE,
                )

    # Ensure mandatory educational disclaimer is present
    if "Aarogya Saathi" not in guarded and "HeartAI does not provide medical diagnoses" not in guarded:
        guarded = f"{guarded.strip()}\n\n---\n**Disclaimer**: {STANDARD_AI_DISCLAIMER}"

    return guarded


def get_gemini_safety_settings() -> list[types.SafetySetting]:
    """Builds official Google GenAI SafetySettings configured for medical education safety."""
    return [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        ),
    ]
