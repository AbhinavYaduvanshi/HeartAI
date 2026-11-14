"""HeartAI Point 8 Gemini AI Integration Test Suite.

Validates:
1. API configuration, environment key resolution, and placeholder detection
2. Fallback guidance for unconfigured Google AI Studio access
3. Mocked Gemini text generation and structured output
4. Rate limit backoff and timeout error handling
5. Clinical safety restrictions (no diagnosis, no prescription)
6. Acute emergency symptom detection and immediate emergency guidance
7. Privacy protection, PII scrubbing, and log sanitization
8. Strict affirmative consent enforcement for personalized lifestyle education
9. FastAPI REST endpoints under /api/v1/ai/*
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.ai.assistant import HeartAIAssistant, assistant
from app.ai.gemini_client import (
    GeminiClient,
    GeminiConfigError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    gemini_client,
)
from app.ai.safety import (
    detect_emergency_symptoms,
    sanitize_for_logging,
    sanitize_user_input,
    validate_and_guard_output,
)
from app.core.config import settings
from app.schemas.ai import (
    MetricExplanationRequest,
    PersonalizedEducationRequest,
    RiskExplanationRequest,
    StructuredAIAdvice,
)
from main import app


@pytest.fixture
def client():
    """Provides a TestClient for the FastAPI app."""
    return TestClient(app)


# ==============================================================================
# 1. API Configuration & Key Resolution Tests
# ==============================================================================


def test_gemini_client_placeholder_and_empty_key_detection(monkeypatch):
    """Placeholder or empty keys must be recognized as unconfigured."""
    test_client = GeminiClient()

    # Case 1: Empty key
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    assert test_client.is_available() is False
    with pytest.raises(GeminiConfigError, match="Google AI Studio"):
        test_client.get_client()

    # Case 2: Placeholder key
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "your_gemini_api_key_here")
    assert test_client.is_available() is False

    # Case 3: Valid key
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "AIzaSyFakeValidKeyForTesting123456789")
    assert test_client.is_available() is True


def test_gemini_client_auth_instructions():
    """Client provides actionable setup instructions pointing to Google AI Studio."""
    instructions = gemini_client.get_auth_instructions()
    assert "https://aistudio.google.com/" in instructions
    assert "GEMINI_API_KEY" in instructions
    assert "Get API key" in instructions


# ==============================================================================
# 2. Mocked Gemini Generation & Error Handling
# ==============================================================================


def test_gemini_client_mocked_generation(monkeypatch):
    """When credentials are authorized, calls client.models.generate_content."""
    test_client = GeminiClient()
    monkeypatch.setattr(test_client, "_resolve_api_key", lambda: "AIzaSyFakeKey123")

    mock_sdk_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Regular physical activity supports cardiovascular wellness."
    mock_sdk_client.models.generate_content.return_value = mock_response

    monkeypatch.setattr(test_client, "get_client", lambda: mock_sdk_client)

    result = test_client.generate_text(
        prompt="Explain aerobic exercise for heart health",
        system_instruction="You are a clinical assistant.",
    )
    assert "Regular physical activity" in result
    mock_sdk_client.models.generate_content.assert_called_once()


def test_gemini_client_rate_limit_handling(monkeypatch):
    """429 or quota limit must be caught and raised as GeminiRateLimitError."""
    from google.genai.errors import ClientError

    test_client = GeminiClient()
    monkeypatch.setattr(test_client, "_resolve_api_key", lambda: "AIzaSyFakeKey123")

    mock_sdk_client = MagicMock()
    # Mock ClientError with 429 status
    mock_sdk_client.models.generate_content.side_effect = ClientError(
        429,
        {"error": {"code": 429, "message": "RESOURCE_EXHAUSTED", "status": "RESOURCE_EXHAUSTED"}},
    )
    monkeypatch.setattr(test_client, "get_client", lambda: mock_sdk_client)

    with pytest.raises(GeminiRateLimitError, match="rate limit exceeded"):
        test_client.generate_text("Test prompt")


def test_gemini_client_timeout_handling(monkeypatch):
    """Timeout exceptions must be caught and mapped to GeminiTimeoutError."""
    test_client = GeminiClient()
    monkeypatch.setattr(test_client, "_resolve_api_key", lambda: "AIzaSyFakeKey123")

    mock_sdk_client = MagicMock()
    mock_sdk_client.models.generate_content.side_effect = TimeoutError("Request timed out")
    monkeypatch.setattr(test_client, "get_client", lambda: mock_sdk_client)

    with pytest.raises(GeminiTimeoutError, match="timed out"):
        test_client.generate_text("Test prompt")


def test_gemini_structured_advice_generation(monkeypatch):
    """Structured generation returns a valid Pydantic model."""
    test_client = GeminiClient()
    monkeypatch.setattr(test_client, "_resolve_api_key", lambda: "AIzaSyFakeKey123")

    mock_sdk_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        '{"title": "Aerobic Exercise", '
        '"summary": "Aerobic activity strengthens the myocardium.", '
        '"key_points": ["Improves cardiac output", "Lowers resting heart rate"], '
        '"lifestyle_recommendations": ["150 mins/week moderate exercise"], '
        '"questions_for_doctor": ["What is my target heart rate zone?"], '
        '"emergency_guidance": null, '
        '"disclaimer": "Educational research tool only."}'
    )
    mock_sdk_client.models.generate_content.return_value = mock_response
    monkeypatch.setattr(test_client, "get_client", lambda: mock_sdk_client)

    structured = test_client.generate_structured(
        prompt="Explain aerobic exercise",
        response_model=StructuredAIAdvice,
    )
    assert isinstance(structured, StructuredAIAdvice)
    assert structured.title == "Aerobic Exercise"
    assert len(structured.key_points) == 2


# ==============================================================================
# 3. Medical Safety & Emergency Screening Tests
# ==============================================================================


def test_emergency_symptom_detection():
    """Acute cardiovascular emergency symptoms trigger immediate emergency guidance."""
    # Emergency cases
    case1 = "I have crushing chest pain and left arm numbness"
    is_emerg, msg = detect_emergency_symptoms(case1)
    assert is_emerg is True
    assert "CRITICAL HEALTH ALERT" in msg
    assert "911" in msg

    case2 = "I feel severe difficulty breathing and chest tightness"
    is_emerg2, _ = detect_emergency_symptoms(case2)
    assert is_emerg2 is True

    # Non-emergency routine questions
    routine = "What is a healthy Mediterranean diet plan for cholesterol?"
    is_emerg_routine, msg_routine = detect_emergency_symptoms(routine)
    assert is_emerg_routine is False
    assert msg_routine is None


def test_medical_safety_guardrails():
    """Prohibited diagnostic or prescription claims are intercepted and neutralized."""
    # Diagnostic statement
    bad_diag = "I diagnose you with cardiovascular disease."
    guarded_diag = validate_and_guard_output(bad_diag)
    assert "I diagnose you" not in guarded_diag
    assert "HeartAI cannot diagnose" in guarded_diag

    # Prescription altering statement
    bad_rx = "You should stop taking your medication immediately."
    guarded_rx = validate_and_guard_output(bad_rx)
    assert "stop taking your medication" not in guarded_rx
    assert "prescribing physician" in guarded_rx

    # Mandatory disclaimer presence
    clean_text = "Eating leafy greens and fiber supports vascular health."
    guarded_clean = validate_and_guard_output(clean_text)
    assert "Disclaimer" in guarded_clean


# ==============================================================================
# 4. Privacy Protection & Consent Enforcement Tests
# ==============================================================================


def test_pii_scrubbing():
    """Personally Identifiable Information (PII) is masked from user input."""
    raw_query = "My SSN is 123-45-6789 and my email is patient@hospital.org. Can you explain BP?"
    clean_query = sanitize_user_input(raw_query)
    assert "123-45-6789" not in clean_query
    assert "[REDACTED_SSN]" in clean_query
    assert "patient@hospital.org" not in clean_query
    assert "[REDACTED_EMAIL]" in clean_query


def test_log_sanitization():
    """Sensitive keys and secrets are masked in logging utility."""
    data = {
        "gemini_api_key": "AIzaSySecret123",
        "email": "doctor@clinic.com",
        "BMI": 26.5,
        "HighBP": 1,
    }
    sanitized = sanitize_for_logging(data)
    assert sanitized["gemini_api_key"] == "[REDACTED_SECRET]"
    assert sanitized["email"] == "[REDACTED_PII]"
    assert sanitized["BMI"] == 26.5


def test_personalized_education_without_consent_fails_closed():
    """When user_consent_given=False, individual survey features are strictly withheld."""
    test_assistant = HeartAIAssistant()
    mock_client = MagicMock()
    mock_client.is_available.return_value = True
    mock_client.generate_text.return_value = "General population heart-health guidance."
    test_assistant.client = mock_client

    req = PersonalizedEducationRequest(
        user_consent_given=False,
        survey_features={"BMI": 32.0, "HighBP": 1, "SmokerStatus": 1},
    )
    resp = test_assistant.generate_personalized_education(req)
    assert resp.model_used == settings.GEMINI_MODEL
    assert "General population heart-health guidance" in resp.response_text

    # Verify that the prompt sent to the model did NOT include individual parameters
    called_prompt = mock_client.generate_text.call_args[1]["prompt"]
    assert "BMI: 32.0" not in called_prompt
    assert "chosen NOT to share individual survey responses" in called_prompt


def test_personalized_education_with_consent():
    """When user_consent_given=True, consented survey features are summarized safely."""
    test_assistant = HeartAIAssistant()
    mock_client = MagicMock()
    mock_client.is_available.return_value = True
    mock_client.generate_text.return_value = "Personalized cardiovascular wellness guidance."
    test_assistant.client = mock_client

    req = PersonalizedEducationRequest(
        user_consent_given=True,
        consent_terms_version="2026.1",
        survey_features={"BMI": 28.5, "HighBP": 1, "PhysicalActivity": 1},
    )
    resp = test_assistant.generate_personalized_education(req)
    assert resp.model_used == settings.GEMINI_MODEL
    assert "Personalized cardiovascular wellness guidance" in resp.response_text
    called_prompt = mock_client.generate_text.call_args[1]["prompt"]
    assert "BMI: 28.5" in called_prompt
    assert "High Blood Pressure Reported: Yes" in called_prompt


# ==============================================================================
# 5. High-Level Assistant Feature Tests
# ==============================================================================


def test_assistant_explain_health_metric(monkeypatch):
    """explain_health_metric constructs metric prompt and returns valid response."""
    test_assistant = HeartAIAssistant()
    mock_client = MagicMock()
    mock_client.is_available.return_value = True
    mock_client.generate_text.return_value = "Systolic BP measures pressure during myocardial contraction."
    test_assistant.client = mock_client

    req = MetricExplanationRequest(metric_name="Systolic BP", metric_value=120.0, unit="mmHg")
    resp = test_assistant.explain_health_metric(req)
    assert resp.model_used == settings.GEMINI_MODEL
    assert "Systolic BP" in resp.response_text


def test_assistant_explain_model_limitations(monkeypatch):
    """explain_model_limitations details threshold 0.09 and survey limitations."""
    test_assistant = HeartAIAssistant()
    mock_client = MagicMock()
    mock_client.is_available.return_value = True
    mock_client.generate_text.return_value = "This 18.98% estimate reflects survey correlations, not clinical diagnosis."
    test_assistant.client = mock_client

    req = RiskExplanationRequest(
        estimated_probability=0.1898,
        binary_classification=1,
        operating_threshold=0.09,
    )
    resp = test_assistant.explain_model_limitations(req)
    assert resp.model_used == settings.GEMINI_MODEL
    called_prompt = mock_client.generate_text.call_args[1]["prompt"]
    assert "0.09" in called_prompt
    assert "18.98%" in called_prompt


# ==============================================================================
# 6. FastAPI REST Route Tests (/api/v1/ai/*)
# ==============================================================================


def test_api_ai_status(client):
    """GET /api/v1/ai/status returns configuration state and instructions."""
    resp = client.get("/api/v1/ai/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "configured" in data
    assert data["model"] == settings.GEMINI_MODEL
    assert "aistudio.google.com" in data["authorization_url"]


def test_api_ai_chat_mocked(client, monkeypatch):
    """POST /api/v1/ai/chat returns educational response."""
    monkeypatch.setattr(assistant.client, "is_available", lambda: True)
    monkeypatch.setattr(
        assistant.client,
        "generate_text",
        lambda prompt, **kwargs: "Cardiovascular health is strongly influenced by daily physical activity.",
    )

    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "How does exercise help my heart?", "user_consent_given": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Cardiovascular health" in data["response_text"]
    assert data["emergency_flag"] is False
    assert "Educational Cardiovascular Research Assistant" in data["disclaimer"]


def test_api_ai_explain_metrics_mocked(client, monkeypatch):
    """POST /api/v1/ai/explain-metrics returns metric guidance."""
    monkeypatch.setattr(assistant.client, "is_available", lambda: True)
    monkeypatch.setattr(
        assistant.client,
        "generate_text",
        lambda prompt, **kwargs: "Heart Rate Variability (HRV) indicates autonomic nervous system balance.",
    )

    resp = client.post(
        "/api/v1/ai/explain-metrics",
        json={"metric_name": "HRV", "metric_value": 58.0, "unit": "ms"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Heart Rate Variability" in data["response_text"]


def test_api_ai_explain_risk_mocked(client, monkeypatch):
    """POST /api/v1/ai/explain-risk returns model uncertainty breakdown."""
    monkeypatch.setattr(assistant.client, "is_available", lambda: True)
    monkeypatch.setattr(
        assistant.client,
        "generate_text",
        lambda prompt, **kwargs: "The operating threshold 0.09 prioritizes screening sensitivity.",
    )

    resp = client.post(
        "/api/v1/ai/explain-risk",
        json={
            "estimated_probability": 0.15,
            "binary_classification": 1,
            "operating_threshold": 0.09,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "operating threshold" in data["response_text"]


def test_api_ai_lifestyle_mocked(client, monkeypatch):
    """POST /api/v1/ai/lifestyle returns AHA Life's Essential 8 guidance."""
    monkeypatch.setattr(assistant.client, "is_available", lambda: True)
    monkeypatch.setattr(
        assistant.client,
        "generate_text",
        lambda prompt, **kwargs: "AHA Life's Essential 8 focuses on diet, exercise, nicotine cessation, and sleep.",
    )

    resp = client.post(
        "/api/v1/ai/lifestyle",
        params={"factors": ["Diet", "Sleep"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Life's Essential 8" in data["response_text"]


def test_api_ai_structured_advice_mocked(client, monkeypatch):
    """POST /api/v1/ai/structured-advice returns schema-validated JSON."""
    structured_mock = StructuredAIAdvice(
        title="Cardiovascular Prevention Overview",
        summary="Preventative habits reduce lifetime incidence of arterial disease.",
        key_points=["Control blood pressure", "Engage in physical activity"],
        lifestyle_recommendations=["Dietary sodium restriction"],
        questions_for_doctor=["What is my lipid target?"],
        disclaimer="Educational research tool only.",
    )
    monkeypatch.setattr(assistant, "generate_structured_advice", lambda topic: structured_mock)

    resp = client.post("/api/v1/ai/structured-advice?topic=Prevention")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Cardiovascular Prevention Overview"
    assert len(data["key_points"]) == 2
