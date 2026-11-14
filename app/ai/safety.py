"""HeartAI Generative AI Medical Safety and Privacy Guardrails.

Enforces clinical safety restrictions, emergency symptom detection,
PII scrubbing, log anonymization, and mandatory educational disclaimers.
"""

from __future__ import annotations

import re
from typing import Any

from google.genai import types

from app.schemas.ai import STANDARD_AI_DISCLAIMER

# Acute emergency trigger patterns requiring immediate emergency guidance
EMERGENCY_KEYWORDS = [
    r"\bcrushing\s+chest\s+pain\b",
    r"\bchest\s+tightness\b",
    r"\bpressure\s+in\s+(my\s+)?chest\b",
    r"\bpain\s+(radiating|spreading)\s+to\s+(my\s+)?(left\s+)?(arm|jaw|neck|back)\b",
    r"\bsevere\s+(shortness\s+of\s+breath|difficulty\s+breathing)\b",
    r"\bcan'?t\s+breathe\b",
    r"\bsudden\s+(numbness|weakness|paralysis)\b",
    r"\bslurred\s+speech\b",
    r"\bfacial\s+droop\b",
    r"\bsudden\s+loss\s+of\s+consciousness\b",
    r"\bpassed\s+out\b",
    r"\bcollapsed\b",
]

EMERGENCY_ALERT_MESSAGE = (
    "🚨 CRITICAL HEALTH ALERT: The symptoms you described may indicate an acute cardiovascular "
    "or medical emergency (such as a heart attack or stroke). "
    "DO NOT WAIT. Call emergency services immediately (911 in the US/Canada, 112 in Europe/India, 999 in the UK, "
    "or your local emergency number), or go to the nearest emergency department right away. "
    "While waiting for medical help, sit or lie down comfortably, stay calm, and do not attempt to drive yourself."
)

# Prohibited clinical diagnosis and prescription patterns
DISALLOWED_MEDICAL_PATTERNS = [
    (r"\b(i\s+diagnose\s+you\s+with|you\s+have\s+been\s+diagnosed\s+with)\b", "diagnosis"),
    (r"\b(stop\s+taking\s+(your\s+)?(medication|medicine|prescriptions?)|discontinue\s+your\s+pills?)\b", "medication_alteration"),
    (r"\b(take\s+\d+\s*(mg|milligrams?|tablets?)|prescribe\s+[a-z]+)\b", "prescription"),
    (r"\b(this\s+prediction\s+is\s+medically\s+verified|confirmed\s+by\s+doctor)\b", "verification_claim"),
    (r"\b(you\s+definitely\s+have\s+heart\s+disease|you\s+will\s+suffer\s+a\s+heart\s+attack)\b", "definitive_claim"),
]

# PII Regex patterns for input scrubbing
PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]"),
    (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "[REDACTED_CARD]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[REDACTED_EMAIL]"),
    (r"\b(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b", "[REDACTED_PHONE]"),
]


def detect_emergency_symptoms(text: str) -> tuple[bool, str | None]:
    """Scans text for acute emergency cardiovascular or neurological symptoms.

    Returns:
        (True, EMERGENCY_ALERT_MESSAGE) if potential emergency indicators found,
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
            if k.lower() in {"password", "secret", "token", "api_key", "gemini_api_key"}:
                masked[k] = "[REDACTED_SECRET]"
            elif k.lower() in {"email", "phone", "name", "address"}:
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
    """Ensures model output contains no prohibited diagnostic or prescriptive claims.

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
                    "HeartAI cannot diagnose medical conditions, but research indicates that",
                    guarded,
                    flags=re.IGNORECASE,
                )
            elif rule_type in {"medication_alteration", "prescription"}:
                guarded = re.sub(
                    pattern,
                    "Never alter or start medication without consulting your prescribing physician",
                    guarded,
                    flags=re.IGNORECASE,
                )
            elif rule_type in {"verification_claim", "definitive_claim"}:
                guarded = re.sub(
                    pattern,
                    "This educational estimate reflects population statistics and is not clinical verification",
                    guarded,
                    flags=re.IGNORECASE,
                )

    # Ensure mandatory educational disclaimer is present
    if "Educational Cardiovascular Research Assistant" not in guarded and "HeartAI does not provide medical diagnoses" not in guarded:
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
