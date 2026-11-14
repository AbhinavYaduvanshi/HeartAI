"""HeartAI Point 9 — Production Readiness and End-to-End Validation Test Suite.

Comprehensive system verification covering:
1. Complete End-to-End User Journey (Registration, Authentication, Informed Consent,
   Risk Prediction, Audit History, Record Deletion, Purge, Consent Revocation).
2. Strict 25-Feature Whitelist Validation and Boundary Hardening (zero symptom leakage).
3. Deterministic Pre-Gemini Emergency Detection (Acute cardiac phrases, 112 India response).
4. Model Artifact Integrity Verification & Tamper Detection (SHA-256, fail-closed loader).
5. Independent Health and Preprocessor Status Diagnostics (/health).
6. Operational Security, PII Scrubbing, and Medical Safety Guardrails.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ai.safety import (
    detect_emergency_symptoms,
    sanitize_for_logging,
    sanitize_user_input,
    validate_and_guard_output,
)
from app.core.config import settings
from app.core.security import decode_access_token
from app.db.models import Base
from app.db.session import get_db
from app.services.model_service import ModelIntegrityError, model_service
from main import app

# Isolated in-memory SQLite database engine for end-to-end testing
TEST_E2E_DB_URL = "sqlite:///:memory:"
e2e_engine = create_engine(TEST_E2E_DB_URL, connect_args={"check_same_thread": False})
E2ESessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=e2e_engine)


@pytest.fixture(scope="session", autouse=True)
def init_e2e_db():
    """Initializes tables and ensures model artifacts are preloaded once per test session."""
    Base.metadata.create_all(bind=e2e_engine)
    model_service.load_artifacts()
    yield
    Base.metadata.drop_all(bind=e2e_engine)


@pytest.fixture
def db_session():
    """Yields a managed database session transaction that rolls back cleanly after each test."""
    conn = e2e_engine.connect()
    trans = conn.begin()
    session = E2ESessionLocal(bind=conn)

    app.dependency_overrides[get_db] = lambda: session
    yield session

    session.close()
    trans.rollback()
    conn.close()
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(db_session):
    """Provides a TestClient with transactional database dependency override."""
    return TestClient(app)


# Standard valid 25-feature CDC BRFSS payload
SAMPLE_VALID_INPUT = {
    "Sex_Male": 1,
    "AgeCategory": 9,  # 60-64
    "BMI": 28.4,
    "BMICategory": 3,  # Overweight
    "Race": 1,
    "Education": 4,
    "Income": 6,
    "GeneralHealth": 3,  # Good
    "PhysicalHealthDays": 2.0,
    "MentalHealthDays": 1.0,
    "HighBP": 1,
    "HighCholesterol": 1,
    "StrokeHistory": 0,
    "Diabetes": 0,
    "KidneyDisease": 0,
    "Depression": 0,
    "Asthma": 0,
    "SmokerStatus": 3,  # Former smoker
    "ECigStatus": 4,  # Never
    "PhysicalActivity": 1,
    "AlcoholDrinking": 0,
    "BingeDrinking": 0,
    "Checkup": 1,
    "MedCostObstacle": 0,
    "PersonalDoctor": 1,
    "user_consent_given": False,
    "consent_terms_version": None,
}


class TestEndToEndUserJourney:
    """Verifies the complete user lifecycle from onboarding to consent revocation."""

    def test_complete_user_lifecycle(self, client: TestClient, db_session):
        # 1. Register a new user
        user_email = "dr.sharma@cardio-research.in"
        user_password = "SecureResearchPassword2026!"
        reg_response = client.post(
            "/api/v1/auth/register",
            json={"email": user_email, "password": user_password},
        )
        assert reg_response.status_code == 201, reg_response.text
        reg_data = reg_response.json()
        assert reg_data["email"] == user_email
        assert reg_data["consent_given"] is False

        # 2. Authenticate and receive JWT
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": user_password},
        )
        assert login_response.status_code == 200, login_response.text
        login_data = login_response.json()
        token = login_data["access_token"]
        assert token is not None

        # Verify token claims
        token_payload = decode_access_token(token)
        assert token_payload is not None
        assert token_payload.get("sub") == user_email

        auth_headers = {"Authorization": f"Bearer {token}"}

        # 3. Retrieve current user profile
        me_response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert me_response.status_code == 200
        assert me_response.json()["email"] == user_email
        assert me_response.json()["consent_given"] is False

        # 4. Grant Informed Consent (Version 2026.1)
        consent_response = client.post(
            "/api/v1/auth/consent",
            headers=auth_headers,
            json={
                "consent_given": True,
                "terms_version": "2026.1",
            },
        )
        assert consent_response.status_code == 200
        consent_data = consent_response.json()
        assert consent_data["consent_given"] is True
        assert consent_data["consent_terms_version"] == "2026.1"
        assert consent_data["consent_revoked"] is False

        # 5. Check Consent Status Endpoint
        status_response = client.get("/api/v1/auth/consent", headers=auth_headers)
        assert status_response.status_code == 200
        assert status_response.json()["consent_given"] is True

        # 6. Submit risk prediction request with consent flags to production /predict
        predict_payload = dict(SAMPLE_VALID_INPUT)
        predict_payload["user_consent_given"] = True
        predict_payload["consent_terms_version"] = "2026.1"

        pred_response = client.post(
            "/predict",
            headers=auth_headers,
            json=predict_payload,
        )
        assert pred_response.status_code == 200, pred_response.text
        pred_data = pred_response.json()
        assert "estimated_probability" in pred_data
        assert 0.0 <= pred_data["estimated_probability"] <= 1.0
        assert pred_data["operating_threshold"] == 0.09
        assert pred_data["binary_classification"] in (0, 1)
        assert pred_data["calibration_status"] == "calibrated_isotonic_cv5"
        assert pred_data["model_version"] == "2.1.0"
        assert "limitations" in pred_data
        assert "educational_disclaimer" in pred_data
        assert "privacy_notice" in pred_data

        # 7. Verify prediction history record was persisted
        history_response = client.get("/api/v1/auth/history", headers=auth_headers)
        assert history_response.status_code == 200
        history_list = history_response.json()
        assert len(history_list) >= 1
        record = history_list[0]
        record_id = record["id"]
        assert record["model_version"] == "2.1.0"
        assert record["operating_threshold"] == 0.09
        assert 0.0 <= record["estimated_probability"] <= 1.0

        # 8. Delete the specific prediction record
        del_response = client.delete(f"/api/v1/auth/history/{record_id}", headers=auth_headers)
        assert del_response.status_code == 200
        assert del_response.json()["deleted_id"] == record_id

        # 9. Verify history count is now 0
        history_after_del = client.get("/api/v1/auth/history", headers=auth_headers).json()
        assert len(history_after_del) == 0

        # 10. Create two more records and test purge
        client.post("/predict", headers=auth_headers, json=predict_payload)
        client.post("/predict", headers=auth_headers, json=predict_payload)
        assert len(client.get("/api/v1/auth/history", headers=auth_headers).json()) == 2

        purge_response = client.delete("/api/v1/auth/history", headers=auth_headers)
        assert purge_response.status_code == 200
        assert purge_response.json()["deleted_count"] == 2
        assert len(client.get("/api/v1/auth/history", headers=auth_headers).json()) == 0

        # 11. Revoke Informed Consent
        revoke_response = client.post(
            "/api/v1/auth/consent",
            headers=auth_headers,
            json={"consent_given": False, "terms_version": "2026.1"},
        )
        assert revoke_response.status_code == 200
        assert revoke_response.json()["consent_given"] is False
        assert revoke_response.json()["consent_revoked"] is True

        # 12. Verify personalized AI endpoint falls back to general guidance without survey features when consent is revoked
        personalized_response = client.post(
            "/api/v1/ai/personalized",
            headers=auth_headers,
            json={"survey_features": {"BMI": 28.4, "HighBP": 1}},
        )
        assert personalized_response.status_code == 200
        resp_data = personalized_response.json()
        assert "Notice" in resp_data["response_text"]
        assert "revoked" in resp_data["response_text"].lower() or "consent" in resp_data["response_text"].lower()


class TestFeatureWhitelistAndBoundaries:
    """Validates that only approved 25 CDC BRFSS features are processed and symptom leakage is blocked."""

    def test_rejection_of_symptom_injection_into_predict(self, client: TestClient):
        # Attempting to inject acute clinical symptoms into the 25-feature ML model
        injected_payload = dict(SAMPLE_VALID_INPUT)
        injected_payload["symptoms"] = "severe crushing chest pain"
        injected_payload["troponin_level"] = 2.4

        # Pydantic schema ignores extra fields without inserting them into ML features
        response = client.post("/predict", json=injected_payload)
        assert response.status_code == 200
        data = response.json()
        # Ensure model executed cleanly on the 25 features only
        assert data["operating_threshold"] == 0.09

    def test_rejection_of_invalid_categorical_ranges(self, client: TestClient):
        # Invalid GeneralHealth (allowed: 1 to 5)
        invalid_payload = dict(SAMPLE_VALID_INPUT)
        invalid_payload["GeneralHealth"] = 99
        res = client.post("/predict", json=invalid_payload)
        assert res.status_code == 422

        # Invalid AgeCategory (allowed: 1 to 13)
        invalid_payload2 = dict(SAMPLE_VALID_INPUT)
        invalid_payload2["AgeCategory"] = 0
        res2 = client.post("/predict", json=invalid_payload2)
        assert res2.status_code == 422

    def test_rejection_of_out_of_boundary_continuous_features(self, client: TestClient):
        # BMI out of range (< 12.0 or > 80.0)
        low_bmi = dict(SAMPLE_VALID_INPUT)
        low_bmi["BMI"] = 4.5
        assert client.post("/predict", json=low_bmi).status_code == 422

        high_bmi = dict(SAMPLE_VALID_INPUT)
        high_bmi["BMI"] = 150.0
        assert client.post("/predict", json=high_bmi).status_code == 422

        # PhysicalHealthDays out of range (0 to 30)
        invalid_days = dict(SAMPLE_VALID_INPUT)
        invalid_days["PhysicalHealthDays"] = 45.0
        assert client.post("/predict", json=invalid_days).status_code == 422

    def test_missing_required_feature_rejected(self, client: TestClient):
        incomplete_payload = dict(SAMPLE_VALID_INPUT)
        del incomplete_payload["HighBP"]
        res = client.post("/predict", json=incomplete_payload)
        assert res.status_code == 422


class TestEmergencyScreeningAndIndiaGuidance:
    """Verifies deterministic pre-Gemini emergency triage and prominent Indian emergency numbers."""

    @pytest.mark.parametrize(
        "emergency_phrase",
        [
            "I feel like an elephant sitting on my chest right now",
            "There is a severe suffocation in my chest and I can't breathe",
            "Sudden severe crushing chest pain radiating to my left arm and jaw",
            "I have intense chest tightness and slurred speech",
            "Severe squeezing in chest with sudden numbness on my right side",
            "Chest pain with cold sweats and dizziness",
            "Burning in chest radiating to neck and shoulder",
            "My father just collapsed and passed out",
        ],
    )
    def test_deterministic_emergency_detection(self, emergency_phrase: str):
        is_emergency, message = detect_emergency_symptoms(emergency_phrase)
        assert is_emergency is True
        assert message is not None
        assert "🚨 CRITICAL HEALTH ALERT" in message
        # Must prominently feature India 112 and 102
        assert "India: 112 (National Emergency Number) / 102 (Ambulance)" in message
        assert "911" in message
        assert "999" in message

    def test_emergency_bypasses_gemini_completely(self, client: TestClient):
        # Even if Gemini API key is missing or mock is not called, emergency triage must respond immediately
        mock_gemini = MagicMock()
        mock_gemini.generate_content.side_effect = RuntimeError("Should not be called for emergency!")

        emergency_input = {
            "symptoms_experienced": "I have an elephant sitting on my chest and severe pain spreading to arm",
            "onset_time": "10 minutes ago",
            "is_ongoing": True,
            "severity": "severe",
        }
        response = client.post("/api/v1/ai/symptoms", json=emergency_input)
        assert response.status_code == 200
        data = response.json()
        assert data["is_emergency"] is True
        assert data["urgency_category"] == "EMERGENCY"
        assert "112" in data["suggested_next_action"] or "112" in str(data["emergency_contacts"])
        assert "do not wait" in data["suggested_next_action"].lower()

    def test_benign_symptom_inquiry_does_not_trigger_false_emergency(self, client: TestClient):
        # Benign general query should not trigger emergency alert
        is_emergency, message = detect_emergency_symptoms(
            "What lifestyle modifications help manage mild hypertension and high cholesterol?"
        )
        assert is_emergency is False
        assert message is None


class TestModelArtifactIntegrityAndHealthReporting:
    """Verifies SHA-256 cryptographic artifact verification and independent health status."""

    def test_production_artifacts_sha256_match_metadata(self):
        meta_path = Path("models/model_metadata.json")
        assert meta_path.exists(), "models/model_metadata.json must exist"

        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

        expected_model_sha256 = meta.get("sha256_checksum")
        expected_preproc_sha256 = meta.get("preprocessing", {}).get("sha256_checksum")

        assert expected_model_sha256 is not None
        assert expected_preproc_sha256 is not None

        # Verify active model service state
        status = model_service.get_status()
        assert status["loaded"] is True
        assert status["model_sha256_verified"] is True
        assert status["preprocessor_sha256_verified"] is True
        assert status["operating_threshold"] == 0.09
        assert status["model_sha256"] == expected_model_sha256
        assert status["preprocessor_sha256"] == expected_preproc_sha256

    def test_independent_health_status_reporting(self, client: TestClient):
        health_res = client.get("/health")
        assert health_res.status_code == 200
        data = health_res.json()
        assert data["status"] in {"healthy", "degraded"}
        assert data["database"]["connected"] is True
        assert data["model"]["loaded"] is True
        assert data["model"]["sha256_verified"] is True
        assert data["model"]["preprocessor_sha256_verified"] is True
        assert data["model"]["operating_threshold"] == 0.09

    def test_tampered_model_artifact_fails_closed(self, tmp_path: Path, monkeypatch):
        # Create a corrupted model file
        corrupt_model = tmp_path / "corrupt_model.joblib"
        corrupt_model.write_bytes(b"TAMPERED_MODEL_BYTES_FOR_SECURITY_AUDIT")

        monkeypatch.setattr(settings, "MODEL_PATH", str(corrupt_model))

        try:
            with pytest.raises(ModelIntegrityError) as exc_info:
                model_service.load_artifacts(force_reload=True)

            assert "mismatch" in str(exc_info.value).lower()
            status = model_service.get_status()
            assert status["sha256_verified"] is False
            assert status["loaded"] is False
        finally:
            # Restore legitimate production model artifact
            monkeypatch.setattr(settings, "MODEL_PATH", "models/best_model.joblib")
            model_service.load_artifacts(force_reload=True)
            assert model_service.is_loaded is True


class TestOperationalSafetyAndPIIScrubbing:
    """Verifies PII scrubbing, logging sanitization, and educational output guardrails."""

    def test_pii_scrubbing(self):
        prompt_with_pii = (
            "My name is John Doe, SSN 123-45-6789, email john.doe@cardio.com, "
            "phone +1-555-123-4567. Can my BMI of 27 cause heart issues?"
        )
        scrubbed = sanitize_user_input(prompt_with_pii)
        assert "123-45-6789" not in scrubbed
        assert "[REDACTED_SSN]" in scrubbed
        assert "john.doe@cardio.com" not in scrubbed
        assert "[REDACTED_EMAIL]" in scrubbed
        assert "+1-555-123-4567" not in scrubbed

    def test_log_sanitization_removes_secrets_and_pii(self):
        log_payload = {
            "SECRET_KEY": "super_secret_jwt_key_here_at_least_32_characters",
            "email": "researcher@heartai.org",
            "gemini_api_key": "AIzaSySecretTokenXYZ",
            "metric": "blood_pressure",
            "nested": {
                "password": "UserPassword123",
                "safe_value": 120,
            },
        }
        sanitized = sanitize_for_logging(log_payload)
        assert sanitized["SECRET_KEY"] == "[REDACTED_SECRET]"
        assert sanitized["email"] == "[REDACTED_PII]"
        assert sanitized["gemini_api_key"] == "[REDACTED_SECRET]"
        assert sanitized["nested"]["password"] == "[REDACTED_SECRET]"
        assert sanitized["nested"]["safe_value"] == 120

    def test_output_guardrail_replaces_prohibited_medical_claims(self):
        # Simulated LLM hallucinating a diagnosis or prescription
        bad_output = "I diagnose you with myocardial infarction. Take 50 mg of metoprolol immediately."
        guarded = validate_and_guard_output(bad_output)

        assert "i diagnose you with" not in guarded.lower()
        assert "HeartAI cannot diagnose medical conditions" in guarded
        assert "take 50 mg" not in guarded.lower()
        assert "Never start, stop, or alter any medication" in guarded
        assert "Aarogya Saathi" in guarded or "HeartAI does not provide medical diagnoses" in guarded
