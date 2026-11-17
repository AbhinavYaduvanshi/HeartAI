"""HeartAI Point 13.1 Pre-Staging Security & Reliability Regression Tests.

Validates all 5 mandatory remediations from Point 13.0 Audit:
1. REL-01: Health-check JSON path (.model.loaded) in deployment and verification scripts.
2. SEC-01: Model import endpoint (/api/v1/models/sync-drive) lockdown (authentication, disablement, path sandbox).
3. REL-03: Separation of Alembic schema management from application startup create_all().
4. SEC-02: Frontend NiceGUI session token management and Bearer header injection.
5. REL-02: Reverse-proxy rate limiting with trusted IP resolution and anti-spoofing guards.
6. Scientific invariants & emergency symptom isolation preservation.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.config import Settings, settings
from app.core.rate_limit import get_trusted_client_ip
from app.db.models import User
from app.db.session import init_db
from app.ml.validation import PatientBRFSSInput
from main import app
from motion_demo import (
    clear_user_session,
    get_auth_headers,
    get_session_middleware_kwargs,
    is_user_authenticated,
)

# ==============================================================================
# Priority 1 — REL-01: Fix Health-Check JSON Paths
# ==============================================================================


def test_deployment_scripts_contain_exact_model_loaded_nested_path():
    """Verify restore_staging.sh and verify_staging.sh query .model.loaded and contain 0 obsolete .model_loaded references."""
    restore_script = Path("deploy/scripts/restore_staging.sh").read_text(encoding="utf-8")
    verify_script = Path("deploy/scripts/verify_staging.sh").read_text(encoding="utf-8")

    # Both scripts must query .model.loaded
    assert ".model.loaded" in restore_script, "restore_staging.sh must query .model.loaded"
    assert ".model.loaded" in verify_script, "verify_staging.sh must query .model.loaded"

    # Neither script must reference the obsolete top-level .model_loaded
    assert ".model_loaded" not in restore_script, "restore_staging.sh contains obsolete .model_loaded reference"
    assert ".model_loaded" not in verify_script, "verify_staging.sh contains obsolete .model_loaded reference"


def test_health_check_response_structure_conformance():
    """Verify the actual /health endpoint response produces nested model.loaded and database.connected."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    # Invariants of HealthResponse
    assert "status" in data
    assert "model" in data
    assert isinstance(data["model"], dict)
    assert "loaded" in data["model"]
    assert "model_loaded" not in data  # Proves top-level key does not exist

    assert "database" in data
    assert isinstance(data["database"], dict)
    assert "connected" in data["database"]


def test_restore_script_health_evaluation_logic():
    """Simulates the shell JSON parsing logic in restore_staging.sh across healthy, degraded, and corrupted payloads."""

    def evaluate_health_json(json_str: str) -> bool:
        try:
            payload = json.loads(json_str)
            status_val = payload.get("status", "failed")
            model_loaded = str(payload.get("model", {}).get("loaded", False)).lower()
            db_connected = str(payload.get("database", {}).get("connected", False)).lower()
            return status_val == "healthy" and model_loaded == "true" and db_connected == "true"
        except Exception:
            return False

    healthy_payload = json.dumps({
        "status": "healthy",
        "model": {"loaded": True, "sha256_verified": True},
        "database": {"connected": True, "dialect": "postgresql"},
    })
    assert evaluate_health_json(healthy_payload) is True

    # Missing model.loaded
    degraded_model = json.dumps({
        "status": "healthy",
        "model": {"loaded": False},
        "database": {"connected": True},
    })
    assert evaluate_health_json(degraded_model) is False

    # Disconnected DB
    disconnected_db = json.dumps({
        "status": "degraded",
        "model": {"loaded": True},
        "database": {"connected": False},
    })
    assert evaluate_health_json(disconnected_db) is False

    # Malformed JSON
    assert evaluate_health_json("{invalid_json: true}") is False
    assert evaluate_health_json("") is False


# ==============================================================================
# Priority 2 — SEC-01: Secure Model Import Endpoint
# ==============================================================================


def test_model_sync_endpoint_rejects_unauthenticated_request():
    """Verify /api/v1/models/sync-drive strictly requires Bearer authentication."""
    client = TestClient(app)
    response = client.post(
        "/api/v1/models/sync-drive",
        json={"source_dir": "models/heartai-rf-v1", "set_active": True},
    )
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


def test_model_sync_endpoint_disabled_by_default_and_forbidden():
    """Verify /api/v1/models/sync-drive rejects authenticated users with HTTP 403 when ENABLE_MODEL_IMPORT is False."""
    client = TestClient(app)

    # Mock user dependency in FastAPI
    mock_user = MagicMock(spec=User)
    mock_user.email = "auditor@heartai.internal"
    mock_user.is_active = True

    from app.api.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = client.post(
            "/api/v1/models/sync-drive",
            json={"source_dir": "models/heartai-rf-v1", "set_active": True},
        )
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()
        assert "SEC-01" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_production_config_rejects_enable_model_import():
    """Verify production and staging settings strictly forbid ENABLE_MODEL_IMPORT=True."""
    valid_key = "ProductionMasterSecretKey2026_HighEntropyToken!"
    with pytest.raises(ValueError, match="ENABLE_MODEL_IMPORT is prohibited in production"):
        Settings(
            APP_ENV="production",
            SECRET_KEY=valid_key,
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://127.0.0.1:6379/0",
            BACKEND_API_URL="https://heartai.internal",
            ENABLE_MODEL_IMPORT=True,
            CORS_ORIGINS=["https://heartai.internal"],
        )

    with pytest.raises(ValueError, match="ENABLE_MODEL_IMPORT is prohibited in staging"):
        Settings(
            APP_ENV="staging",
            SECRET_KEY=valid_key,
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://127.0.0.1:6379/0",
            ENABLE_MODEL_IMPORT=True,
            CORS_ORIGINS=["https://heartai.internal"],
        )


def test_model_sync_rejects_path_traversal_when_import_enabled():
    """Verify path containment: arbitrary filesystem paths outside models/ are rejected even if enabled in dev."""
    mock_user = MagicMock(spec=User)
    mock_user.email = "dev@heartai.internal"
    mock_user.is_active = True

    from app.api.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        with patch.object(settings, "ENABLE_MODEL_IMPORT", True), \
             patch.object(settings, "APP_ENV", "development"):

            client = TestClient(app)
            # Attempt traversal outside models directory
            response = client.post(
                "/api/v1/models/sync-drive",
                json={"source_dir": "/etc/shadow", "set_active": True},
            )
            assert response.status_code == 400
            assert "must reside within" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ==============================================================================
# Priority 3 — REL-03: Separate Alembic from Startup
# ==============================================================================


def test_init_db_skips_create_all_in_production():
    """Verify init_db() does NOT call Base.metadata.create_all in production mode."""
    with patch.object(settings, "APP_ENV", "production"), \
         patch("app.db.session.check_db_connection", return_value=(True, "postgresql")), \
         patch("app.db.session.Base.metadata.create_all") as mock_create_all:

        init_db()
        mock_create_all.assert_not_called()


def test_init_db_raises_on_connection_failure_in_production():
    """Verify init_db() raises RuntimeError if database check fails in production mode."""
    with patch.object(settings, "APP_ENV", "production"), \
         patch("app.db.session.check_db_connection", return_value=(False, "postgresql")), \
         patch("app.db.session.Base.metadata.create_all"):

        with pytest.raises(RuntimeError, match="Database connectivity check failed"):
            init_db()


def test_init_db_allows_create_all_in_development():
    """Verify init_db() calls Base.metadata.create_all in development mode for local SQLite development."""
    with patch.object(settings, "APP_ENV", "development"), \
         patch("app.db.session.Base.metadata.create_all") as mock_create_all:

        init_db()
        mock_create_all.assert_called_once()


# ==============================================================================
# Priority 4 — SEC-02: Correct Frontend Authentication & Session Storage
# ==============================================================================


def test_frontend_auth_helpers_unauthenticated_state():
    """Verify session helpers return unauthenticated state when storage is empty."""
    from nicegui import app as nicegui_app

    mock_storage = MagicMock()
    mock_storage.user = {}
    with patch.object(nicegui_app, "storage", mock_storage):
        assert is_user_authenticated() is False
        assert get_auth_headers() == {}


def test_frontend_auth_helpers_authenticated_state():
    """Verify get_auth_headers() injects Bearer token when valid session exists in app.storage.user."""
    from nicegui import app as nicegui_app

    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_payload"
    mock_storage = MagicMock()
    mock_storage.user = {
        "access_token": fake_token,
        "user_email": "physician@hospital.org",
        "is_authenticated": True,
    }
    with patch.object(nicegui_app, "storage", mock_storage):
        assert is_user_authenticated() is True
        headers = get_auth_headers()
        assert headers == {"Authorization": f"Bearer {fake_token}"}


def test_frontend_clear_user_session():
    """Verify clear_user_session() purges access_token and updates is_authenticated to False."""
    from nicegui import app as nicegui_app

    fake_storage = {
        "access_token": "some_token",
        "user_email": "physician@hospital.org",
        "is_authenticated": True,
    }
    mock_storage = MagicMock()
    mock_storage.user = fake_storage
    with patch.object(nicegui_app, "storage", mock_storage):
        clear_user_session()
        assert "access_token" not in fake_storage
        assert "user_email" not in fake_storage
        assert fake_storage.get("is_authenticated") is False
        assert is_user_authenticated() is False


def test_frontend_session_middleware_kwargs_environment_sensitive():
    """Verify session cookie https_only is environment-sensitive (Point 13.2B).

    In staging and production, enforces https_only=True so the cookie carries the Secure flag.
    In development, https_only=False permits local evaluation.
    """
    with patch.object(settings, "APP_ENV", "production"):
        assert get_session_middleware_kwargs() == {"https_only": True}

    with patch.object(settings, "APP_ENV", "staging"):
        assert get_session_middleware_kwargs() == {"https_only": True}

    with patch.object(settings, "APP_ENV", "development"):
        assert get_session_middleware_kwargs() == {"https_only": False}

    with patch.object(settings, "APP_ENV", "test"):
        assert get_session_middleware_kwargs() == {"https_only": False}


# ==============================================================================
# Priority 5 — REL-02: Reverse-Proxy Rate Limiting & Anti-Spoofing (Point 13.2B)
# ==============================================================================


def create_mock_request(client_ip: str, headers: dict[str, str] | None = None) -> Request:
    """Helper creating a Starlette Request with specific client socket host and headers."""
    raw_headers = []
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))

    scope = {
        "type": "http",
        "client": (client_ip, 50000),
        "headers": raw_headers,
    }
    return Request(scope)


def test_trusted_client_ip_from_untrusted_direct_connection():
    """Verify get_trusted_client_ip ignores spoofed X-Forwarded-For when connecting directly from untrusted IP."""
    # Untrusted external client 198.51.100.5 tries to spoof header as 10.0.0.1
    req = create_mock_request(
        client_ip="198.51.100.5",
        headers={"X-Forwarded-For": "10.0.0.1", "X-Real-IP": "10.0.0.1"},
    )
    resolved_ip = get_trusted_client_ip(req)
    assert resolved_ip == "198.51.100.5", "Must ignore forwarded headers from untrusted connection"


def test_trusted_client_ip_from_trusted_reverse_proxy_x_real_ip():
    """Verify get_trusted_client_ip trusts X-Real-IP when request connects from 127.0.0.1 (Nginx)."""
    req = create_mock_request(
        client_ip="127.0.0.1",
        headers={
            "X-Real-IP": "203.0.113.195",
            "X-Forwarded-For": "client.spoofed.ip, 203.0.113.195",
        },
    )
    resolved_ip = get_trusted_client_ip(req)
    assert resolved_ip == "203.0.113.195", "Must use X-Real-IP when set by reverse proxy"


def test_trusted_client_ip_from_trusted_reverse_proxy_x_forwarded_for_fallback():
    """Verify fallback prefers the rightmost proxy-appended address (parts[-1]) when X-Real-IP is absent (Point 13.2B)."""
    # In Nginx $proxy_add_x_forwarded_for, client-supplied headers are leftmost,
    # and the proxy appends the real client socket IP at the end (rightmost).
    req = create_mock_request(
        client_ip="127.0.0.1",
        headers={"X-Forwarded-For": "10.0.0.1, 10.0.0.2, 198.51.100.42"},
    )
    resolved_ip = get_trusted_client_ip(req)
    assert resolved_ip == "198.51.100.42", "Must take rightmost proxy-appended IP, rejecting leftmost spoofed entries"


def test_trusted_client_ip_no_headers_from_trusted_proxy():
    """Verify get_trusted_client_ip falls back gracefully to proxy host when no forwarding headers are present."""
    req = create_mock_request(client_ip="127.0.0.1")
    resolved_ip = get_trusted_client_ip(req)
    assert resolved_ip == "127.0.0.1"


# ==============================================================================
# Priority 3 Hardening — REL-03: Systemd Alembic Pre-Start Enforcement (Point 13.2B)
# ==============================================================================


def test_systemd_backend_service_enforces_alembic_exec_start_pre():
    """Verify deploy/systemd/heartai-backend.service enforces alembic upgrade head in ExecStartPre."""
    service_path = Path("deploy/systemd/heartai-backend.service")
    assert service_path.exists(), "heartai-backend.service unit file must exist"
    content = service_path.read_text(encoding="utf-8")

    # 1. Dependency ordering
    assert "After=network.target postgresql.service redis.service" in content
    assert "Wants=postgresql.service redis.service" in content

    # 2. Service execution environment
    assert "User=heartai" in content
    assert "WorkingDirectory=/opt/heartai" in content
    assert "EnvironmentFile=/opt/heartai/.env" in content

    # 3. ExecStartPre precedes ExecStart
    assert "ExecStartPre=/opt/heartai/.venv/bin/alembic upgrade head" in content
    assert "ExecStart=/opt/heartai/.venv/bin/gunicorn -c deploy/gunicorn.conf.py main:app" in content

    pre_idx = content.find("ExecStartPre=/opt/heartai/.venv/bin/alembic upgrade head")
    start_idx = content.find("ExecStart=/opt/heartai/.venv/bin/gunicorn")
    assert 0 <= pre_idx < start_idx, "ExecStartPre must execute strictly before ExecStart"


# ==============================================================================
# Scientific Invariants & Emergency Isolation Verification
# ==============================================================================


def test_scientific_invariants_preserved():
    """Verify bit-level preservation of ML artifacts, threshold, and feature schema."""
    import hashlib

    # 1. Model SHA-256
    with open("models/best_model.joblib", "rb") as f:
        model_hash = hashlib.sha256(f.read()).hexdigest()
    assert model_hash == "5dc415201016ed1223fd1f4c9cb295e14b2dd64639ad507d63efb16bed51f890"

    # 2. Preprocessor SHA-256
    with open("models/preprocessing_pipeline.joblib", "rb") as f:
        prep_hash = hashlib.sha256(f.read()).hexdigest()
    assert prep_hash == "3a354b5f6fb66bfce97bfc2ad2d92303e46d98a3e093e7069fefa213afc67055"

    # 3. Calibrated Operating Threshold
    assert settings.OPERATING_THRESHOLD == 0.09

    # 4. Canonical Feature Count
    feature_fields = list(PatientBRFSSInput.model_fields.keys())
    assert len(feature_fields) == 25

    # 5. Emergency Symptoms Strictly Isolated from ML Schema
    symptom_fields = {"chest_pain", "shortness_of_breath", "dizziness", "palpitations"}
    overlap = symptom_fields.intersection(set(feature_fields))
    assert len(overlap) == 0, f"Symptoms must never enter ML feature schema: {overlap}"
