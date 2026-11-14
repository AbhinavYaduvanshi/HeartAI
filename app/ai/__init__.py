"""HeartAI Generative AI Integration Package (Google Gemini)."""

from app.ai.assistant import HeartAIAssistant, assistant
from app.ai.gemini_client import (
    GeminiAPIError,
    GeminiClient,
    GeminiConfigError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    gemini_client,
)
from app.ai.safety import detect_emergency_symptoms, sanitize_user_input, validate_and_guard_output

__all__ = [
    "HeartAIAssistant",
    "assistant",
    "GeminiClient",
    "gemini_client",
    "GeminiAPIError",
    "GeminiConfigError",
    "GeminiRateLimitError",
    "GeminiTimeoutError",
    "detect_emergency_symptoms",
    "sanitize_user_input",
    "validate_and_guard_output",
]
