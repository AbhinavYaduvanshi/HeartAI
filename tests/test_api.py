"""Tests for HeartAI FastAPI Endpoints and Clinical Model Inference."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_root_health_status():
    """Verify system health endpoint and active model introspection."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "active_model" in data


def test_list_models_endpoint():
    """Verify model registry listing endpoint."""
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    models = response.json()
    assert isinstance(models, list)
    assert len(models) >= 1
    first = models[0]
    assert "model_id" in first
    assert "sha256_checksum" in first
    assert "metrics" in first


def test_predict_endpoint_high_risk():
    """Verify predictive inference endpoint on a symptomatic high-risk patient."""
    payload = {
        "age": 67.0,
        "sex": 1,
        "cp": 0,
        "trestbps": 165.0,
        "chol": 290.0,
        "fbs": 1,
        "restecg": 2,
        "thalach": 115.0,
        "exang": 1,
        "oldpeak": 3.4,
        "slope": 2,
        "ca": 2,
        "thal": 3,
    }
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "risk_probability" in data
    assert "risk_category" in data
    assert "primary_risk_factors" in data
    assert data["prediction_label"] in {0, 1}
    assert len(data["primary_risk_factors"]) > 0


def test_predict_endpoint_low_risk():
    """Verify predictive inference endpoint on a young, healthy patient."""
    payload = {
        "age": 28.0,
        "sex": 0,
        "cp": 2,
        "trestbps": 110.0,
        "chol": 165.0,
        "fbs": 0,
        "restecg": 0,
        "thalach": 178.0,
        "exang": 0,
        "oldpeak": 0.0,
        "slope": 0,
        "ca": 0,
        "thal": 2,
    }
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_probability"] < 0.50
    assert data["prediction_label"] == 0
