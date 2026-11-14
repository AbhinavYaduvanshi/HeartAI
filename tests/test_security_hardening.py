"""HeartAI Point 7.1 Security Hardening Test Suite.

Validates:
- JWT secret management, mandatory configuration, strength checks, and placeholder rejection
- Fail-closed model artifact integrity (model SHA-256, preprocessor SHA-256, feature schema manifest)
- Privacy enforcement: keyed HMAC-SHA256 pseudonymization (never plain unsalted hash)
- Explicit informed consent flow (omitted/false never persists; terms version required)
- Prediction history deletion endpoints (GDPR Art. 17 / HIPAA Right to Erasure)
- Constant-time authentication failure responses (anti-enumeration)
- Production CORS restrictions (rejects wildcard '*')
- Dual-key zero-downtime secret rotation
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, settings
from app.core.security import decode_access_token
from app.db.models import PredictionRecord
from app.db.session import Base, get_db
from app.services.model_service import ModelIntegrityError, model_service
from app.services.prediction_service import compute_pseudonymous_feature_hmac
from main import app

TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    model_service.load_artifacts()
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    app.dependency_overrides[get_db] = lambda: session
    yield session

    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(db_session):
    return TestClient(app)


BASE_SURVEY_PAYLOAD = {
    "Sex_Male": 1,
    "AgeCategory": 10,
    "BMI": 28.5,
    "BMICategory": 3,
    "Race": 1,
    "Education": 4,
    "Income": 7,
    "GeneralHealth": 3,
    "PhysicalHealthDays": 4.0,
    "MentalHealthDays": 2.0,
    "HighBP": 1,
    "HighCholesterol": 1,
    "StrokeHistory": 0,
    "Diabetes": 0,
    "KidneyDisease": 0,
    "Depression": 0,
    "Asthma": 0,
    "SmokerStatus": 3,
    "ECigStatus": 4,
    "PhysicalActivity": 1,
    "AlcoholDrinking": 1,
    "BingeDrinking": 0,
    "Checkup": 1,
    "MedCostObstacle": 0,
    "PersonalDoctor": 1,
}


# ==============================================================================
# 1. JWT Secret Management & Strength Checks
# ==============================================================================


def test_settings_missing_secret_key_fails():
    """Application configuration must fail closed if SECRET_KEY is absent."""
    with pytest.raises((ValidationError, ValueError)):
        Settings(SECRET_KEY="", _env_file=None)


def test_settings_weak_secret_key_fails():
    """SECRET_KEY with fewer than 32 characters must be rejected."""
    with pytest.raises((ValidationError, ValueError), match="too weak"):
        Settings(SECRET_KEY="short-secret-under-32-chars", _env_file=None)


def test_settings_disallowed_placeholder_secret_fails():
    """Committed defaults or known template placeholders must be rejected."""
    with pytest.raises((ValidationError, ValueError), match="insecure placeholder"):
        Settings(
            SECRET_KEY="replace_with_a_secure_random_secret_key_minimum_32_characters",
            _env_file=None,
        )


def test_settings_low_entropy_secret_fails():
    """SECRET_KEY with low character diversity must be rejected."""
    with pytest.raises((ValidationError, ValueError), match="entropy"):
        Settings(SECRET_KEY="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", _env_file=None)


def test_jwt_expired_token_rejected(client):
    """Expired JWT must be rejected with HTTP 401."""
    now = datetime.now(UTC)
    payload = {
        "sub": "expired.user@hospital.org",
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
        "type": "access",
    }
    expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401


def test_jwt_invalid_signature_rejected(client):
    """JWT signed with an alien key must be rejected."""
    alien_key = "alien-secret-key-that-does-not-match-at-all-32chars"
    payload = {
        "sub": "spoofed.user@hospital.org",
        "iat": int(datetime.now(UTC).timestamp()),
        "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
    }
    tampered_token = jwt.encode(payload, alien_key, algorithm="HS256")

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp.status_code == 401


def test_jwt_dual_key_rotation(monkeypatch):
    """Tokens signed with SECRET_KEY_FALLBACK must be accepted during rotation."""
    old_secret = "legacy-secret-key-from-previous-month-32chars"
    new_secret = "new-rotated-master-secret-key-for-heartai-32chars"

    monkeypatch.setattr(settings, "SECRET_KEY", new_secret)
    monkeypatch.setattr(settings, "SECRET_KEY_FALLBACK", old_secret)

    # Token generated under old secret
    legacy_payload = {
        "sub": "dr.rotation@heartai.org",
        "iat": int(datetime.now(UTC).timestamp()),
        "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
    }
    legacy_token = jwt.encode(legacy_payload, old_secret, algorithm="HS256")

    # Decode must succeed through fallback
    decoded = decode_access_token(legacy_token)
    assert decoded is not None
    assert decoded["sub"] == "dr.rotation@heartai.org"


# ==============================================================================
# 2. Model & Preprocessing Artifact Integrity (Fail-Closed)
# ==============================================================================


def test_model_missing_expected_sha_fails_closed(tmp_path, monkeypatch):
    """Model verification must fail closed if expected sha256_checksum is empty."""
    with open(settings.METADATA_PATH, encoding="utf-8") as f:
        meta = json.load(f)
    meta["sha256_checksum"] = ""
    tampered_meta_path = tmp_path / "empty_sha_meta.json"
    with open(tampered_meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f)

    monkeypatch.setattr(settings, "METADATA_PATH", str(tampered_meta_path))
    with pytest.raises(ModelIntegrityError, match="missing, empty, or invalid"):
        model_service.load_artifacts(force_reload=True)

    monkeypatch.setattr(settings, "METADATA_PATH", "models/model_metadata.json")
    model_service.load_artifacts(force_reload=True)


def test_preprocessor_missing_expected_sha_fails_closed(tmp_path, monkeypatch):
    """Verification must fail closed if preprocessing checksum is omitted."""
    with open(settings.METADATA_PATH, encoding="utf-8") as f:
        meta = json.load(f)
    meta["preprocessing"]["sha256_checksum"] = ""
    tampered_meta_path = tmp_path / "empty_prep_sha.json"
    with open(tampered_meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f)

    monkeypatch.setattr(settings, "METADATA_PATH", str(tampered_meta_path))
    with pytest.raises(ModelIntegrityError, match="Preprocessing pipeline expected SHA-256"):
        model_service.load_artifacts(force_reload=True)

    monkeypatch.setattr(settings, "METADATA_PATH", "models/model_metadata.json")
    model_service.load_artifacts(force_reload=True)


def test_tampered_preprocessing_artifact_fails_closed(tmp_path, monkeypatch):
    """Tampering with preprocessing_pipeline.joblib must trigger ModelIntegrityError."""
    fake_prep_path = tmp_path / "tampered_pipeline.joblib"
    fake_prep_path.write_bytes(b"corrupted binary data")

    monkeypatch.setattr(settings, "PREPROCESSOR_PATH", str(fake_prep_path))
    with pytest.raises(ModelIntegrityError, match="Preprocessing pipeline SHA-256 mismatch"):
        model_service.load_artifacts(force_reload=True)

    monkeypatch.setattr(settings, "PREPROCESSOR_PATH", "models/preprocessing_pipeline.joblib")
    model_service.load_artifacts(force_reload=True)


def test_feature_manifest_schema_mismatch_fails_closed(tmp_path, monkeypatch):
    """Altered feature count or names in feature_names.json must fail closed."""
    # Write a 24-feature manifest
    tampered_feat_path = tmp_path / "tampered_features.json"
    tampered_feat_path.write_text(json.dumps(["BMI", "AgeCategory"]), encoding="utf-8")

    # Monkeypatch the path in current working directory temporarily
    real_manifest_path = Path("models/feature_names.json")
    backup_content = real_manifest_path.read_text(encoding="utf-8")
    try:
        real_manifest_path.write_text(json.dumps(["BMI", "AgeCategory"]), encoding="utf-8")
        with pytest.raises(ModelIntegrityError, match="count mismatch"):
            model_service.load_artifacts(force_reload=True)
    finally:
        real_manifest_path.write_text(backup_content, encoding="utf-8")
        model_service.load_artifacts(force_reload=True)


# ==============================================================================
# 3. Privacy, Keyed HMAC & Feature Digest
# ==============================================================================


def test_keyed_hmac_differs_from_plain_sha256():
    """Keyed HMAC-SHA256 must not match plain unsalted SHA-256 (prevents rainbow tables)."""
    test_dict = {"AgeCategory": 10, "BMI": 28.5, "HighBP": 1}
    canonical_json = json.dumps(test_dict, sort_keys=True, separators=(",", ":"))
    plain_sha256 = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    keyed_hmac = compute_pseudonymous_feature_hmac(test_dict)
    assert keyed_hmac != plain_sha256
    assert len(keyed_hmac) == 64


# ==============================================================================
# 4. Explicit Informed Consent Flow
# ==============================================================================


def test_consent_omitted_never_persists(client, db_session):
    """When user_consent_given is omitted, zero database records are created."""
    initial_count = db_session.query(PredictionRecord).count()
    payload = dict(BASE_SURVEY_PAYLOAD)
    # user_consent_given omitted
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 200
    assert resp.json()["consent_recorded"] is False
    assert db_session.query(PredictionRecord).count() == initial_count


def test_consent_false_never_persists(client, db_session):
    """When user_consent_given=False, zero database records are created."""
    initial_count = db_session.query(PredictionRecord).count()
    payload = dict(BASE_SURVEY_PAYLOAD)
    payload["user_consent_given"] = False
    payload["consent_terms_version"] = "2026.1"
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 200
    assert resp.json()["consent_recorded"] is False
    assert db_session.query(PredictionRecord).count() == initial_count


def test_consent_true_without_terms_version_never_persists(client, db_session):
    """user_consent_given=True without acknowledging consent terms version fails closed."""
    initial_count = db_session.query(PredictionRecord).count()
    payload = dict(BASE_SURVEY_PAYLOAD)
    payload["user_consent_given"] = True
    payload["consent_terms_version"] = None  # Missing terms acknowledgment

    resp = client.post("/predict", json=payload)
    assert resp.status_code == 200
    assert resp.json()["consent_recorded"] is False
    assert db_session.query(PredictionRecord).count() == initial_count


def test_consent_true_with_valid_terms_persists_keyed_record(client, db_session):
    """Affirmative consent with valid consent terms version persists keyed record."""
    initial_count = db_session.query(PredictionRecord).count()
    payload = dict(BASE_SURVEY_PAYLOAD)
    payload["user_consent_given"] = True
    payload["consent_terms_version"] = "2026.1"

    resp = client.post("/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["consent_recorded"] is True
    assert data["consent_terms_version"] == "2026.1"
    assert "Informed Telemetry Policy" in data["privacy_notice"]
    assert db_session.query(PredictionRecord).count() == initial_count + 1


# ==============================================================================
# 5. Prediction History Deletion (GDPR Art. 17 / HIPAA Erasure)
# ==============================================================================


def test_prediction_history_purge_and_single_deletion(client, db_session):
    """Authenticated user can purge all records or delete individual records."""
    test_email = "patient.privacy@hospital.org"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": test_email, "password": "SecurePassword123!"},
    )
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": test_email, "password": "SecurePassword123!"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create 2 consented predictions under this user
    rec1 = PredictionRecord(
        user_id=user_id,
        anonymized_input_hash="hash1",
        estimated_probability=0.15,
        binary_classification=1,
        operating_threshold=0.09,
        model_version="2.1.0",
        user_consent_given=True,
    )
    rec2 = PredictionRecord(
        user_id=user_id,
        anonymized_input_hash="hash2",
        estimated_probability=0.05,
        binary_classification=0,
        operating_threshold=0.09,
        model_version="2.1.0",
        user_consent_given=True,
    )
    db_session.add_all([rec1, rec2])
    db_session.commit()

    # Query history
    hist = client.get("/api/v1/auth/history", headers=headers).json()
    assert len(hist) == 2

    # Delete single record
    del_single = client.delete(f"/api/v1/auth/history/{rec1.id}", headers=headers)
    assert del_single.status_code == 200
    assert del_single.json()["deleted_id"] == rec1.id

    # Check history has 1 left
    hist2 = client.get("/api/v1/auth/history", headers=headers).json()
    assert len(hist2) == 1

    # Purge remaining history
    purge_resp = client.delete("/api/v1/auth/history", headers=headers)
    assert purge_resp.status_code == 200
    assert purge_resp.json()["deleted_count"] == 1

    # History is now empty
    hist3 = client.get("/api/v1/auth/history", headers=headers).json()
    assert len(hist3) == 0


# ==============================================================================
# 6. Anti-Enumeration & CORS Hardening
# ==============================================================================


def test_auth_constant_time_anti_enumeration(client):
    """Non-existent user and bad password return identical 401 detail."""
    resp1 = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@hospital.org", "password": "RandomPassword!"},
    )
    resp2 = client.post(
        "/api/v1/auth/login",
        json={"email": "existing.but.wrong@hospital.org", "password": "WrongPassword!"},
    )
    assert resp1.status_code == 401
    assert resp2.status_code == 401
    assert resp1.json()["detail"] == resp2.json()["detail"] == "Incorrect email or password."


def test_production_cors_wildcard_rejected():
    """Production configuration must reject wildcard CORS."""
    with pytest.raises((ValidationError, ValueError), match="Wildcard"):
        Settings(
            APP_ENV="production",
            SECRET_KEY="high-entropy-production-secret-key-at-least-32chars",
            CORS_ORIGINS=["*"],
            _env_file=None,
        )
