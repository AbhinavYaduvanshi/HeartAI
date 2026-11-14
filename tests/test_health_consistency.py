"""HeartAI Point 7.2 Health Status Consistency Regression Tests.

Validates independent artifact integrity reporting:
1. Both artifacts verified -> 200 OK, status="healthy", model_sha256_verified=True, preprocessor_sha256_verified=True
2. Model verified but preprocessor not verified -> status="degraded", preprocessor_sha256_verified=False
3. Preprocessor verified but model not verified -> status="degraded", sha256_verified=False, model_sha256_verified=False
4. Both artifacts failed verification -> status="degraded", both False
5. Missing verification status in status dictionary defaults to False, never True
6. ModelHealthStatus Pydantic schema defaults: fields default to False, loaded=False
7. ModelService independent verification attributes: model_sha256_verified and preprocessor_sha256_verified
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.schemas.health import ModelHealthStatus
from app.services.model_service import model_service
from main import app


@pytest.fixture
def client():
    """Provides a TestClient for the FastAPI app."""
    return TestClient(app)


def test_health_both_artifacts_verified(client, monkeypatch):
    """When both model and preprocessor are verified, /health reports 'healthy' with both True."""
    monkeypatch.setattr(
        model_service,
        "get_status",
        lambda: {
            "loaded": True,
            "model_id": "heartai_voting_ensemble_calibrated",
            "version": "2.1.0",
            "sha256_verified": True,
            "model_sha256_verified": True,
            "preprocessor_sha256_verified": True,
            "operating_threshold": 0.09,
            "feature_count": 25,
        },
    )

    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "healthy"
    model_data = data["model"]
    assert model_data["loaded"] is True
    assert model_data["sha256_verified"] is True
    assert model_data["model_sha256_verified"] is True
    assert model_data["preprocessor_sha256_verified"] is True


def test_health_model_verified_preprocessor_failed(client, monkeypatch):
    """When model is verified but preprocessor is NOT verified, status must be 'degraded'."""
    monkeypatch.setattr(
        model_service,
        "get_status",
        lambda: {
            "loaded": True,
            "model_id": "heartai_voting_ensemble_calibrated",
            "version": "2.1.0",
            "sha256_verified": True,
            "model_sha256_verified": True,
            "preprocessor_sha256_verified": False,
            "operating_threshold": 0.09,
            "feature_count": 25,
        },
    )

    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "degraded"
    model_data = data["model"]
    assert model_data["loaded"] is True
    assert model_data["sha256_verified"] is True
    assert model_data["model_sha256_verified"] is True
    assert model_data["preprocessor_sha256_verified"] is False


def test_health_preprocessor_verified_model_failed(client, monkeypatch):
    """When preprocessor is verified but model is NOT verified, status must be 'degraded'."""
    monkeypatch.setattr(
        model_service,
        "get_status",
        lambda: {
            "loaded": True,
            "model_id": "heartai_voting_ensemble_calibrated",
            "version": "2.1.0",
            "sha256_verified": False,
            "model_sha256_verified": False,
            "preprocessor_sha256_verified": True,
            "operating_threshold": 0.09,
            "feature_count": 25,
        },
    )

    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "degraded"
    model_data = data["model"]
    assert model_data["loaded"] is True
    assert model_data["sha256_verified"] is False
    assert model_data["model_sha256_verified"] is False
    assert model_data["preprocessor_sha256_verified"] is True


def test_health_both_artifacts_failed(client, monkeypatch):
    """When both artifacts failed verification, status must be 'degraded' and both False."""
    monkeypatch.setattr(
        model_service,
        "get_status",
        lambda: {
            "loaded": True,
            "model_id": "heartai_voting_ensemble_calibrated",
            "version": "2.1.0",
            "sha256_verified": False,
            "model_sha256_verified": False,
            "preprocessor_sha256_verified": False,
            "operating_threshold": 0.09,
            "feature_count": 25,
        },
    )

    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "degraded"
    model_data = data["model"]
    assert model_data["loaded"] is True
    assert model_data["sha256_verified"] is False
    assert model_data["model_sha256_verified"] is False
    assert model_data["preprocessor_sha256_verified"] is False


def test_health_missing_verification_defaults_to_false(client, monkeypatch):
    """When verification keys are completely omitted, they must default to False (fail-closed)."""
    # Empty status dictionary
    monkeypatch.setattr(
        model_service,
        "get_status",
        lambda: {
            "loaded": True,
            "model_id": "heartai_voting_ensemble_calibrated",
            "version": "2.1.0",
        },
    )

    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "degraded"
    model_data = data["model"]
    assert model_data["sha256_verified"] is False
    assert model_data["model_sha256_verified"] is False
    assert model_data["preprocessor_sha256_verified"] is False


def test_model_health_status_schema_defaults():
    """ModelHealthStatus Pydantic model must have fail-closed False defaults."""
    status_obj = ModelHealthStatus()
    assert status_obj.loaded is False
    assert status_obj.sha256_verified is False
    assert status_obj.model_sha256_verified is False
    assert status_obj.preprocessor_sha256_verified is False
    assert status_obj.model_id == "unknown"
    assert status_obj.version == "unknown"


def test_model_service_independent_attributes_after_load():
    """ModelService must populate model_sha256_verified and preprocessor_sha256_verified independently."""
    model_service.load_artifacts(force_reload=True)
    status_dict = model_service.get_status()

    assert hasattr(model_service, "model_sha256_verified")
    assert hasattr(model_service, "preprocessor_sha256_verified")
    assert model_service.model_sha256_verified is True
    assert model_service.preprocessor_sha256_verified is True
    assert status_dict["model_sha256_verified"] is True
    assert status_dict["preprocessor_sha256_verified"] is True
    assert status_dict["sha256_verified"] is True
