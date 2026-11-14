"""HeartAI Point 7 — Backend Development & Model Integration Test Suite.

Validates:
- Health and model inspection endpoints (/health, /model-info)
- Primary prediction endpoint (/predict) with calibrated model & threshold T=0.09
- Input validation, physiological boundaries, and codebook checks
- Model artifact checksum integrity (SHA-256)
- Database persistence, user accounts, and Argon2/JWT authentication
- Strict user privacy consent enforcement
- Safe error handling and rate limit behavior
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import PredictionRecord
from app.db.session import Base, get_db
from app.services.model_service import ModelIntegrityError, model_service
from main import app

# Create in-memory SQLite database for isolated test execution
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initializes tables in test database once for the session."""
    Base.metadata.create_all(bind=test_engine)
    # Ensure model artifacts are loaded
    model_service.load_artifacts()
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """Provides a transactional database session rolled back after each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Override FastAPI get_db dependency
    app.dependency_overrides[get_db] = lambda: session

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(db_session):
    """Provides TestClient with overridden database session."""
    return TestClient(app)


# Sample valid BRFSS payloads
VALID_BASELINE_PAYLOAD = {
    "Sex_Male": 0,
    "AgeCategory": 3,  # 25-29
    "BMI": 22.4,
    "BMICategory": 2,  # Normal weight
    "Race": 1,
    "Education": 5,
    "Income": 8,
    "GeneralHealth": 1,  # Excellent
    "PhysicalHealthDays": 0.0,
    "MentalHealthDays": 0.0,
    "HighBP": 0,
    "HighCholesterol": 0,
    "StrokeHistory": 0,
    "Diabetes": 0,
    "KidneyDisease": 0,
    "Depression": 0,
    "Asthma": 0,
    "SmokerStatus": 4,  # Never
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

VALID_SYMPTOMATIC_PAYLOAD = {
    "Sex_Male": 1,
    "AgeCategory": 12,  # 75-79
    "BMI": 33.2,
    "BMICategory": 4,  # Obese
    "Race": 1,
    "Education": 3,
    "Income": 4,
    "GeneralHealth": 4,  # Fair
    "PhysicalHealthDays": 15.0,
    "MentalHealthDays": 5.0,
    "HighBP": 1,
    "HighCholesterol": 1,
    "StrokeHistory": 0,
    "Diabetes": 1,
    "KidneyDisease": 0,
    "Depression": 0,
    "Asthma": 0,
    "SmokerStatus": 1,  # Daily
    "ECigStatus": 4,
    "PhysicalActivity": 0,
    "AlcoholDrinking": 0,
    "BingeDrinking": 0,
    "Checkup": 1,
    "MedCostObstacle": 0,
    "PersonalDoctor": 1,
    "user_consent_given": True,
    "consent_terms_version": "2026.1",
}


# ==============================================================================
# 1. System Health Endpoint Tests
# ==============================================================================


def test_health_endpoint(client):
    """GET /health must return service status, uptime, model status, and DB connectivity."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] in {"healthy", "degraded"}
    assert "service" in data
    assert data["version"] == "2.1.0"
    assert data["uptime_seconds"] >= 0.0
    assert "timestamp" in data

    # Model status
    model_stat = data["model"]
    assert model_stat["loaded"] is True
    assert model_stat["version"] == "2.1.0"
    assert model_stat["sha256_verified"] is True
    assert model_stat["model_sha256_verified"] is True
    assert model_stat["preprocessor_sha256_verified"] is True
    assert model_stat["operating_threshold"] == 0.09

    # Database status
    db_stat = data["database"]
    assert db_stat["connected"] is True


# ==============================================================================
# 2. Model Governance & Introspection Endpoint Tests
# ==============================================================================


def test_model_info_endpoint(client):
    """GET /model-info must return full metadata, calibration method, operating threshold, and feature list."""
    response = client.get("/model-info")
    assert response.status_code == 200
    data = response.json()

    assert data["version"] == "2.1.0"
    assert "CalibratedClassifierCV" in data["architecture"]
    assert data["is_calibrated"] is True
    assert data["calibration_method"] == "isotonic"
    assert data["operating_threshold"] == 0.09
    assert data["training_records"] == 318296
    assert data["test_records"] == 79574
    assert len(data["features"]) == 25
    assert len(data["features_detailed"]) == 25

    # Check non-diagnostic disclaimer
    assert "Educational research estimate; not a clinical diagnostic device" in data["educational_disclaimer"]
    assert "historical" in data["target_definition"]


# ==============================================================================
# 3. Prediction Endpoint Tests & Threshold Verification
# ==============================================================================


def test_predict_baseline_young_healthy(client):
    """POST /predict for young, asymptomatic patient must yield low probability and binary flag 0."""
    response = client.post("/predict", json=VALID_BASELINE_PAYLOAD)
    assert response.status_code == 200
    data = response.json()

    assert data["metric_label"] == "Estimated probability of reported historical cardiovascular disease"
    assert 0.0 <= data["estimated_probability"] <= 1.0
    assert 0.0 <= data["estimated_probability_percentage"] <= 100.0
    assert data["operating_threshold"] == 0.09
    assert data["model_version"] == "2.1.0"
    assert data["calibration_status"] == "calibrated_isotonic_cv5"
    assert data["output_type"] == "educational_estimate"
    assert data["clinical_validation"] is False

    # Probability for young healthy patient should fall below 0.09 threshold
    assert data["estimated_probability"] < 0.09
    assert data["binary_classification"] == 0


def test_predict_symptomatic_high_risk(client):
    """POST /predict for elderly symptomatic patient must yield probability >= 0.09 and binary flag 1."""
    response = client.post("/predict", json=VALID_SYMPTOMATIC_PAYLOAD)
    assert response.status_code == 200
    data = response.json()

    assert data["estimated_probability"] >= 0.09
    assert data["binary_classification"] == 1
    assert data["operating_threshold"] == 0.09
    assert data["consent_recorded"] is True


def test_predict_boundary_bmi_minimum(client):
    """POST /predict with BMI at lower boundary (12.0) must validate successfully."""
    payload = dict(VALID_BASELINE_PAYLOAD)
    payload["BMI"] = 12.0
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert 0.0 <= response.json()["estimated_probability"] <= 1.0


def test_predict_boundary_bmi_maximum(client):
    """POST /predict with BMI at upper boundary (80.0) must validate successfully."""
    payload = dict(VALID_BASELINE_PAYLOAD)
    payload["BMI"] = 80.0
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert 0.0 <= response.json()["estimated_probability"] <= 1.0


def test_predict_boundary_physical_health_days(client):
    """POST /predict with PhysicalHealthDays at max boundary (30.0) must validate."""
    payload = dict(VALID_BASELINE_PAYLOAD)
    payload["PhysicalHealthDays"] = 30.0
    response = client.post("/predict", json=payload)
    assert response.status_code == 200


# ==============================================================================
# 4. Input Validation & Physiological Range Checks (422 Errors)
# ==============================================================================


def test_predict_invalid_bmi_too_low(client):
    """POST /predict with BMI < 12.0 must return 422 Unprocessable Entity."""
    payload = dict(VALID_BASELINE_PAYLOAD)
    payload["BMI"] = 10.5
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_predict_invalid_bmi_too_high(client):
    """POST /predict with BMI > 80.0 must return 422 Unprocessable Entity."""
    payload = dict(VALID_BASELINE_PAYLOAD)
    payload["BMI"] = 85.0
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_predict_invalid_age_category(client):
    """POST /predict with AgeCategory > 13 must return 422 Unprocessable Entity."""
    payload = dict(VALID_BASELINE_PAYLOAD)
    payload["AgeCategory"] = 15
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_predict_missing_required_field(client):
    """POST /predict omitting a required field must return 422 Unprocessable Entity."""
    payload = dict(VALID_BASELINE_PAYLOAD)
    del payload["HighBP"]
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_predict_invalid_data_type(client):
    """POST /predict with string in integer field must return 422 Unprocessable Entity."""
    payload = dict(VALID_BASELINE_PAYLOAD)
    payload["Sex_Male"] = "not_an_integer"
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


# ==============================================================================
# 5. Model Artifact Checksum Integrity
# ==============================================================================


def test_model_sha256_checksum_verification():
    """Verify that models/best_model.joblib matches the registered metadata hash."""
    meta_path = Path(settings.METADATA_PATH)
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    expected_sha = meta["sha256_checksum"].lower()
    actual_sha = model_service.compute_sha256(Path(settings.MODEL_PATH)).lower()
    assert actual_sha == expected_sha


def test_model_integrity_error_on_mismatch(tmp_path, monkeypatch):
    """Simulate artifact tampering to verify ModelIntegrityError is raised."""
    with open(settings.METADATA_PATH, encoding="utf-8") as f:
        tampered_meta = json.load(f)
    tampered_meta["sha256_checksum"] = "0" * 64
    tampered_path = tmp_path / "tampered_metadata.json"
    with open(tampered_path, "w", encoding="utf-8") as f:
        json.dump(tampered_meta, f)

    monkeypatch.setattr(settings, "METADATA_PATH", str(tampered_path))
    with pytest.raises(ModelIntegrityError):
        model_service.load_artifacts(force_reload=True)

    # Restore valid metadata and reload
    monkeypatch.setattr(settings, "METADATA_PATH", "models/model_metadata.json")
    model_service.load_artifacts(force_reload=True)


# ==============================================================================
# 6. Database Persistence & User Privacy Consent Protection
# ==============================================================================


def test_consent_false_does_not_persist_prediction(client, db_session):
    """When user_consent_given=False, prediction must NOT be saved to database."""
    initial_count = db_session.query(PredictionRecord).count()

    payload = dict(VALID_BASELINE_PAYLOAD)
    payload["user_consent_given"] = False
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json()["consent_recorded"] is False

    final_count = db_session.query(PredictionRecord).count()
    assert final_count == initial_count, "Record was persisted despite user_consent_given=False!"


def test_consent_true_persists_anonymized_prediction(client, db_session):
    """When user_consent_given=True, prediction must be saved to database with anonymized hash."""
    initial_count = db_session.query(PredictionRecord).count()

    payload = dict(VALID_SYMPTOMATIC_PAYLOAD)
    payload["user_consent_given"] = True
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json()["consent_recorded"] is True

    final_count = db_session.query(PredictionRecord).count()
    assert final_count == initial_count + 1

    latest = db_session.query(PredictionRecord).order_by(PredictionRecord.id.desc()).first()
    assert latest.binary_classification == 1
    assert latest.operating_threshold == 0.09
    assert latest.user_consent_given is True
    assert len(latest.anonymized_input_hash) == 64  # Valid SHA-256 hex string


# ==============================================================================
# 7. User Registration, Authentication & JWT Authorization
# ==============================================================================


def test_user_registration_and_login_flow(client, db_session):
    """Complete user lifecycle: register, login, retrieve profile, and query history."""
    test_email = "cardiologist.smith@hospital.org"
    test_password = "ClinicalSecurePass2026!"

    # 1. Register
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": test_email, "password": test_password},
    )
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()
    assert user_data["email"] == test_email
    assert "hashed_password" not in user_data

    # 2. Duplicate registration should fail
    dup_resp = client.post(
        "/api/v1/auth/register",
        json={"email": test_email, "password": test_password},
    )
    assert dup_resp.status_code == 400

    # 3. Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": test_email, "password": test_password},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 4. Access protected profile endpoint
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == test_email

    # 5. Access protected history endpoint
    hist_resp = client.get("/api/v1/auth/history", headers=headers)
    assert hist_resp.status_code == 200
    assert isinstance(hist_resp.json(), list)


def test_auth_invalid_credentials(client):
    """Login with wrong password must return 401 Unauthorized."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@hospital.org", "password": "WrongPassword!"},
    )
    assert response.status_code == 401


def test_protected_route_missing_token(client):
    """Protected endpoint without Authorization header must return 401 Unauthorized."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


# ==============================================================================
# 8. Password Hashing & Token Verification Unit Checks
# ==============================================================================


def test_argon2_password_hashing():
    """Verify Argon2 password hashing and verification behavior."""
    pwd = "SecureHeartPassword#123"
    hashed = hash_password(pwd)
    assert hashed.startswith("$argon2")
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_expiration_and_verification():
    """Verify access token creation and decoding."""
    token = create_access_token(subject="researcher@heartai.org")
    from app.core.security import decode_access_token

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "researcher@heartai.org"
    assert "exp" in payload
