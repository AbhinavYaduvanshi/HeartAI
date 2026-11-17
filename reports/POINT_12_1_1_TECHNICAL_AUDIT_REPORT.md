# HeartAI — Point 12.1.1: Deployment Foundations Technical Audit Report

**Date**: November 16, 2026  
**Auditor**: Antigravity Autonomous Technical Verification System  
**Baseline Git Commit**: `fbfc50784f146b5951b585f6c779a9cc7687476c` (origin/main synchronized)  
**Audit Scope**: Deployment Foundations, Alembic Migration Schema, Redis Rate Limiting, Production Configuration Hardening, Nginx Reverse Proxy, Systemd Process Supervision, and Dependency Invariants  
**Final Audit Verdict**: **`READY FOR POINT 12.2`** (PostgreSQL Infrastructure & Database Staging)

---

## 1. Executive Summary & Audit Overview

Following the implementation of **Point 12.1 (Application Configuration & Deployment Foundations)**, this technical audit was executed under **Point 12.1.1** to independently verify every architectural component, configuration validator, migration script, reverse proxy specification, and process supervisor before authorizing any active database provisioning (Point 12.2).

### Summary of Audit Outcomes:
1. **Alembic Metadata Completeness**: 100% attribute, constraint, and index parity verified between `app/db/models.py` (`Base.metadata`) and `alembic/versions/001_initial_schema.py`. Full reversible upgrade (`head`) and downgrade (`base`) lifecycle tested and verified.
2. **Redis Rate Limiting Security**: `app/core/rate_limit.py` fails closed in `production` and `staging` when `REDIS_URL` is omitted, prohibiting silent in-memory fallback. Connection test diagnostics are strictly sanitized to prevent credential exposure.
3. **Fail-Closed Configuration**: Pydantic v2 model validators in `app/core/config.py` enforce non-bypassable constraints across all configuration sources: rejecting SQLite, debug mode, localhost backend URLs, and wildcard CORS in production.
4. **Nginx & WebSocket Forwarding**: `deploy/nginx/heartai.conf` implements route isolation between FastAPI backend (`127.0.0.1:8000`) and NiceGUI frontend (`127.0.0.1:8080`), with proper dynamic `$connection_upgrade` mapping for WebSockets and complete security headers.
5. **Systemd & Process Isolation**: Service units enforce non-root execution (`heartai:heartai`), secure secret injection via `EnvironmentFile`, and strict OS isolation (`ProtectSystem=full`, `PrivateTmp=true`).
6. **Test Suite & Invariants**: Full test suite passed with **174/174 tests passing (100%)**, zero Ruff linter warnings, and bit-level preservation of ML model artifacts (SHA-256 hashes, 0.09 operating threshold, 25-feature BRFSS input schema).

---

## 2. Git Baseline & Repository Integrity Audit

### 2.1 Git Status & Commit Alignment
- **Active Branch**: `main`
- **HEAD Commit**: `fbfc50784f146b5951b585f6c779a9cc7687476c` (Point 11.3 push)
- **Remote Tracking**: `origin/main` at `fbfc50784f146b5951b585f6c779a9cc7687476c` (Fully synchronized)
- **Working Tree State**: Controlled audit state. Uncommitted changes are staged for technical review; zero unauthorized commits or remote pushes were executed.

### 2.2 Modified Tracked Files
| File Path | Changes | Purpose |
| :--- | :---: | :--- |
| `DEPLOYMENT_GUIDE.md` | +6 / -6 | Updated deployment prerequisites for PostgreSQL 16 and Redis 7. |
| `ENVIRONMENT_CONFIGURATION.md` | +61 / -46 | Documented production fail-closed variables, mandatory secrets, and Redis storage settings. |
| `app/core/config.py` | +43 / -4 | Added Pydantic v2 `@model_validator(mode="after")` enforcing production invariants. |
| `app/core/rate_limit.py` | +43 / -4 | Added `resolve_storage_uri()` fail-closed logic and sanitized `test_redis_ping()`. |
| `motion_demo.py` | +9 / -2 | Added dynamic environment binding for NiceGUI frontend port (`FRONTEND_PORT`). |
| `requirements.txt` | +4 / -0 | Added `alembic>=1.13.0` and `redis>=5.0.0`. |

### 2.3 Untracked Deployment Assets
| Asset Path | Nature | Purpose |
| :--- | :--- | :--- |
| `alembic.ini` | Config | Alembic environment configuration file. |
| `alembic/env.py` | Migration Script | Alembic migration runtime connecting to `Settings.DATABASE_URL`. |
| `alembic/script.py.mako` | Template | Migration generation template. |
| `alembic/versions/001_initial_schema.py` | Migration | Revision `001` creating `users` and `prediction_records`. |
| `deploy/nginx/heartai.conf` | Web Server Config | Nginx reverse proxy template with WebSocket mapping and TLS 1.3. |
| `deploy/redis/redis.conf` | Cache Config | Hardened Redis 7 configuration template. |
| `deploy/systemd/heartai-backend.service` | Supervisor Unit | Systemd service definition for FastAPI backend. |
| `deploy/systemd/heartai-frontend.service` | Supervisor Unit | Systemd service definition for NiceGUI frontend. |
| `deploy/gunicorn.conf.py` | WSGI/ASGI Config | Gunicorn process configuration with Uvicorn workers. |
| `deploy/.env.production.template` | Env Template | Production environment variable template. |
| `tests/test_deployment_foundations.py` | Test Suite | 12 automated tests for configuration, Alembic, and Redis. |
| `POINT_12_INFRASTRUCTURE_ASSESSMENT_AND_DEPLOYMENT_PLAN.md` | Report | Point 12.0 assessment and roadmap deliverable. |
| `POINT_12_1_IMPLEMENTATION_REPORT.md` | Report | Point 12.1 deployment foundations report. |

---

## 3. Alembic Schema & SQLAlchemy Metadata Completeness Audit

### 3.1 Metadata Parity Matrix
A field-by-field verification was performed comparing `Base.metadata` from `app/db/models.py` against `alembic/versions/001_initial_schema.py`.

#### Table: `users`
| Column / Constraint | SQLAlchemy Model (`app/db/models.py`) | Alembic Migration (`001_initial_schema.py`) | Parity Status |
| :--- | :--- | :--- | :---: |
| `id` | `Column(Integer, primary_key=True, index=True)` | `sa.Column('id', sa.Integer(), primary_key=True)` | **MATCH** |
| `email` | `Column(String(255), unique=True, index=True, nullable=False)` | `sa.Column('email', sa.String(255), nullable=False)` | **MATCH** |
| `hashed_password` | `Column(String(255), nullable=False)` | `sa.Column('hashed_password', sa.String(255), nullable=False)` | **MATCH** |
| `full_name` | `Column(String(100), nullable=True)` | `sa.Column('full_name', sa.String(100), nullable=True)` | **MATCH** |
| `role` | `Column(String(20), default="patient", nullable=False)` | `sa.Column('role', sa.String(20), server_default='patient', nullable=False)` | **MATCH** |
| `is_active` | `Column(Boolean, default=True, nullable=False)` | `sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False)` | **MATCH** |
| `consent_given` | `Column(Boolean, default=False, nullable=False)` | `sa.Column('consent_given', sa.Boolean(), server_default=sa.text('0'), nullable=False)` | **MATCH** |
| `consent_timestamp`| `Column(DateTime(timezone=True), nullable=True)` | `sa.Column('consent_timestamp', sa.DateTime(timezone=True), nullable=True)` | **MATCH** |
| `created_at` | `Column(DateTime(timezone=True), server_default=func.now(), nullable=False)` | `sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False)` | **MATCH** |
| `updated_at` | `Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)` | `sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)` | **MATCH** |
| Indexes | `ix_users_id`, `ix_users_email` (unique=True) | `op.create_index('ix_users_id', ...)` & `op.create_index('ix_users_email', ..., unique=True)` | **MATCH** |

#### Table: `prediction_records`
| Column / Constraint | SQLAlchemy Model (`app/db/models.py`) | Alembic Migration (`001_initial_schema.py`) | Parity Status |
| :--- | :--- | :--- | :---: |
| `id` | `Column(Integer, primary_key=True, index=True)` | `sa.Column('id', sa.Integer(), primary_key=True)` | **MATCH** |
| `user_id` | `Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)` | `sa.Column('user_id', sa.Integer(), nullable=True)` | **MATCH** |
| `anonymized_input_hash` | `Column(String(64), index=True, nullable=False)` | `sa.Column('anonymized_input_hash', sa.String(64), nullable=False)` | **MATCH** |
| `raw_input_encrypted` | `Column(Text, nullable=True)` | `sa.Column('raw_input_encrypted', sa.Text(), nullable=True)` | **MATCH** |
| `estimated_probability` | `Column(Float, nullable=False)` | `sa.Column('estimated_probability', sa.Float(), nullable=False)` | **MATCH** |
| `operating_threshold` | `Column(Float, default=0.09, nullable=False)` | `sa.Column('operating_threshold', sa.Float(), server_default='0.09', nullable=False)` | **MATCH** |
| `predicted_category` | `Column(Integer, nullable=False)` | `sa.Column('predicted_category', sa.Integer(), nullable=False)` | **MATCH** |
| `clinical_summary` | `Column(Text, nullable=True)` | `sa.Column('clinical_summary', sa.Text(), nullable=True)` | **MATCH** |
| `created_at` | `Column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)` | `sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False)` | **MATCH** |
| Foreign Key | `ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL')` | `op.create_foreign_key('fk_prediction_records_user_id_users', 'prediction_records', 'users', ['user_id'], ['id'], ondelete='SET NULL')` | **MATCH** |
| Indexes | `ix_prediction_records_id`, `ix_..._hash`, `ix_..._created_at` | `op.create_index` for all 3 indexes | **MATCH** |

### 3.2 Upgrade and Downgrade Lifecycle Verification
In automated test `test_alembic_upgrade_downgrade_lifecycle`:
1. Executed `command.upgrade(cfg, "head")` against an isolated database:
   - Verified schema generation: `users`, `prediction_records`, and `alembic_version` created.
   - Column schema inspection matched 100% of defined fields and types.
2. Executed `command.downgrade(cfg, "base")`:
   - Verified complete table destruction in reverse dependency order: `prediction_records` dropped first, followed by `users`.
   - Verified zero orphan indexes or residual tables remaining.

### 3.3 Runtime Safety & SQLite Isolation
- **Application Startup Behavior**: Inspected `app/db/session.py`. `init_db()` executes `Base.metadata.create_all(bind=engine)` only for development/testing SQLite databases. It does **not** invoke Alembic programmatic commands automatically at application startup. Schema migrations remain explicitly controlled through administrative CLI execution (`alembic upgrade head`).
- **SQLite Database Integrity**: Existing SQLite databases (`data/heartai.db`) are not altered or locked by Alembic runtime configuration.

---

## 4. Redis Rate Limiting & Storage Security Audit

### 4.1 Storage Resolution & In-Memory Fallback Prevention
- **Module Audited**: `app/core/rate_limit.py`.
- **Fail-Closed Verification**:
  ```python
  def resolve_storage_uri() -> str:
      if settings.APP_ENV in {"production", "staging"}:
          if not settings.REDIS_URL or not settings.REDIS_URL.strip():
              raise RuntimeError(
                  f"REDIS_URL must be configured in {settings.APP_ENV} mode to enforce "
                  "distributed rate limiting across multi-worker processes. In-memory fallback is prohibited."
              )
          return settings.REDIS_URL
      return settings.REDIS_URL if settings.REDIS_URL else "memory://"
  ```
  In `production` or `staging`, any attempt to launch the application without an active, non-empty `REDIS_URL` raises a fatal `RuntimeError`. The insecure `memory://` fallback is physically restricted to `development` and `testing` modes.

### 4.2 Credential Sanitization Audit & Remediation
- **Defect Identified During Audit**: The initial implementation of `test_redis_ping()` returned `f"Redis connection failed: {err}"`. In certain edge cases, connection libraries (such as `redis-py`) could format the URL or host/port into the exception string, creating a theoretical risk of credential or internal IP reflection.
- **Remediation Implemented**: Hardened `test_redis_ping()` to sanitize all outputs:
  ```python
  except Exception as err:
      logger.warning("Redis ping failed: %s", type(err).__name__)
      return False, f"Redis connection failed ({type(err).__name__})."
  ```
  Diagnostics, health endpoints, and application logs now return strictly generic exception class names (e.g., `ConnectionError`, `TimeoutError`), guaranteeing zero credential exposure.

### 4.3 Rate Limit Preservation
- Verified that strict per-endpoint thresholds remain fully enforced:
  - `/api/v1/predict`: 30 requests/minute.
  - `/api/v1/auth/login`: 5 requests/minute.
  - `/api/v1/auth/register`: 5 requests/minute.
  - Aarogya Saathi AI chat: 10 requests/minute.
- Rate limits are preserved identically whether backed by Redis or development in-memory storage.

### 4.4 Operational Testing Distinction
- **Unit & Mock Testing**: Automated tests (`test_rate_limit_storage_resolution`, `test_redis_ping_unconfigured`, `test_redis_ping_unreachable`) verify fallback prevention, error handling, and parameter validation.
- **Operational Integration Testing**: A live distributed rate-limiting test across concurrent Gunicorn worker processes requires an active Redis daemon. This is explicitly documented for execution during Point 12.2 / Point 12.3 on the staging VM.

---

## 5. Production Configuration Security Audit

### 5.1 Fail-Closed Configuration Matrix (`app/core/config.py`)
All configuration constraints are validated post-instantiation via Pydantic v2 `@model_validator(mode="after")`.

| Rule / Constraint | Behavior in Development | Behavior in Staging / Production | Automated Test Verification |
| :--- | :--- | :--- | :--- |
| **Database Engine** | SQLite allowed (`sqlite:///...`) | SQLite **strictly prohibited** (`ValueError`) | `test_production_config_rejects_sqlite` |
| **Debug Mode** | `APP_DEBUG=True` allowed | `APP_DEBUG=True` **strictly prohibited** | `test_production_config_rejects_debug_mode` |
| **Rate Limit Storage** | In-memory fallback (`memory://`) | `REDIS_URL` **mandatory** (`ValueError`) | `test_production_config_rejects_missing_redis` |
| **Backend API URL** | `http://localhost:8000` allowed | Localhost/127.0.0.1 **strictly prohibited** | `test_production_config_rejects_localhost_backend_url` |
| **CORS Origins** | Localhost & dev ports allowed | Localhost **prohibited**; Wildcard `*` **strictly prohibited** | `test_production_config_rejects_wildcard_cors` |
| **Secret Key** | Placeholder blocked | Minimum 32 chars, high entropy, placeholder blocked | `test_production_config_rejects_weak_secrets` |

### 5.2 Bypass Analysis
- **Direct Environment Variables (`os.environ`)**: Processed by Pydantic's `SettingsConfigDict` and validated through `model_validator`.
- **`.env` File Injection**: Read by Pydantic and passed through identical validation.
- **Programmatic Keyword Instantiation (`Settings(...)`)**: Instantiation triggers `model_validator(mode="after")`.
- **Verdict**: Zero configuration bypass pathways exist. Any invalid setting halts application boot immediately.

---

## 6. Nginx Reverse Proxy & WebSocket Transport Audit

### 6.1 Route Separation & Proxy Targets
- **FastAPI Backend (`127.0.0.1:8000`)**:
  - `location ~ ^/(api|predict|health|model-info|docs|redoc|openapi.json)`
  - Buffering enabled; timeouts: connect 10s, read 60s.
- **NiceGUI Frontend & WebSockets (`127.0.0.1:8080`)**:
  - `location /`
  - HTTP 1.1 enabled; timeouts: read 86400s, send 86400s (required for persistent interactive WebSockets).
- **Static Assets Direct Delivery**:
  - `location /static/` -> `/opt/heartai/static/`
  - Served directly from disk with 30-day client cache header, bypassing Python application runtimes.

### 6.2 WebSocket Upgrade Mapping Remediation
- **Defect Identified**: The initial template hardcoded `proxy_set_header Connection "upgrade";` for all requests on `location /`. While effective for WebSocket handshakes, this header is non-standard for normal HTTP/1.1 requests.
- **Remediation Implemented**: Implemented standard Nginx connection upgrade mapping:
  ```nginx
  map $http_upgrade $connection_upgrade {
      default upgrade;
      ''      close;
  }
  ```
  Updated `location /` to:
  ```nginx
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection $connection_upgrade;
  ```
  Standard HTTP requests receive `Connection: close` (or keep-alive), while WebSocket requests receive `Connection: upgrade`.

### 6.3 Security Headers & Port Isolation
- **Headers Enforced**:
  - `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' wss: https:;`
- **Port Exposure**: Backend ports 8000 and 8080 bind exclusively to `127.0.0.1` (loopback). Nginx is the sole publicly accessible listener on ports 80 and 443.

---

## 7. Systemd Services & Gunicorn Process Management Audit

### 7.1 Security Sandboxing & Least Privilege
Both `heartai-backend.service` and `heartai-frontend.service` implement comprehensive Linux kernel isolation:
- `User=heartai` / `Group=heartai` (dedicated unprivileged service account).
- `NoNewPrivileges=true` (prevents privilege escalation via setuid binaries).
- `PrivateTmp=true` (allocates an isolated `/tmp` namespace per unit).
- `ProtectSystem=full` (mounts `/usr`, `/boot`, and `/etc` read-only).
- `ProtectHome=true` (renders `/root`, `/home`, and `/run/user` inaccessible).
- `ReadWritePaths=/opt/heartai/logs /opt/heartai/data` (strictly whitelisted write paths).

### 7.2 Secret Protection in Process Tables
- Secrets (JWT signing keys, database passwords, Gemini API keys) are loaded exclusively via `EnvironmentFile=/opt/heartai/.env`.
- No sensitive arguments are passed on the CLI (`ExecStart`), ensuring that process listings (`ps aux`, `htop`, `/proc/<pid>/cmdline`) never expose production credentials.

### 7.3 Target Host Adaptations Required for Ubuntu 24.04 VM (Point 12.2 Prerequisites)
The following pre-flight setup must be executed during staging provisioning:
1. Create system user and group: `sudo useradd --system --shell /bin/false heartai`.
2. Provision application directory tree: `sudo mkdir -p /opt/heartai/{logs,data,static}`.
3. Establish directory ownership: `sudo chown -R heartai:heartai /opt/heartai`.
4. Create Python 3.12 virtual environment at `/opt/heartai/venv`.

---

## 8. Dependency & Environment Reproducibility Audit

### 8.1 Added Dependencies
- `alembic>=1.13.0`: Fully compatible with SQLAlchemy 2.0; verified via automated migration tests.
- `redis>=5.0.0`: Modern Redis client supporting connection pooling, SSL/TLS, and sentinel; verified.

### 8.2 Dependency Invariants
- **`pyarrow` Absence**: Verified 100% absent from active virtual environment, `requirements.txt`, and runtime imports. No custom import interceptors or `sitecustomize.py` workarounds exist.
- **Dependency Reproducibility**: Prior to production cutover in Point 12.3, generating a locked constraint file (`requirements.lock`) via `pip-tools` is recommended to prevent upstream transitives from shifting.

---

## 9. Automated Test Execution & Model Invariants Audit

### 9.1 Test Suite Results
- **Pytest Execution**: `python -m pytest -q`
- **Tests Evaluated**: 174 automated tests across 17 test modules.
- **Status**: **174 passed, 0 failed, 0 skipped** (Execution time: 19.52s).
- **Ruff Linter**: `python -m ruff check .` -> **All checks passed (0 errors, 0 warnings)**.

### 9.2 Scientific & Model Invariant Verification
| Invariant Parameter | Canonical Benchmark Requirement | Verified Value | Status |
| :--- | :--- | :--- | :---: |
| **Model Artifact SHA-256** | `5dc415201016ed1223fd1f4c9cb295e14b2dd64639ad507d63efb16bed51f890` | `5dc4...890` (`models/best_model.joblib`) | **EXACT MATCH** |
| **Preprocessor SHA-256** | `3a354b5f6fb66bfce97bfc2ad2d92303e46d98a3e093e7069fefa213afc67055` | `3a35...055` (`models/preprocessing_pipeline.joblib`) | **EXACT MATCH** |
| **Operating Threshold** | `0.09` | `0.09` | **EXACT MATCH** |
| **Input Feature Schema** | Exactly 25 CDC BRFSS features | 25 features (`models/feature_names.json`) | **EXACT MATCH** |
| **Historical Recall** | 79.6% (Retrospective classification) | 0.7960 (`recall_sensitivity`) | **EXACT MATCH** |
| **Historical Specificity**| 74.3% (Retrospective classification) | 0.7430 (`specificity`) | **EXACT MATCH** |
| **Symptom Isolation** | Emergency symptoms isolated from tabular ML | Preserved in triage safety rules | **CONFIRMED** |

---

## 10. Defect Register & Resolution Log

| Defect ID | Severity | Description | Resolution Status |
| :--- | :---: | :--- | :---: |
| **DEF-12.1-01** | Medium | `test_redis_ping()` exception string could reflect URL/credentials. | **Resolved**: Hardened to return sanitized `type(err).__name__`. |
| **DEF-12.1-02** | Low | Nginx `Connection "upgrade"` was hardcoded for all HTTP requests on `/`. | **Resolved**: Added `map $http_upgrade $connection_upgrade` and dynamic variable. |
| **DEF-12.1-03** | Low | Pytest discovery matched imported helper `test_redis_ping`. | **Resolved**: Aliased import to `ping_redis` in test file. |
| **DEF-12.1-04** | Info | Temporary SQLite file locking during test teardown on Windows. | **Resolved**: Explicit `engine.dispose()` added prior to directory teardown. |

---

## 11. Final Audit Verdict & Next Phase Readiness

### Final Audit Verdict:
# **`READY FOR POINT 12.2`**

### Authorization Status & Boundaries:
- Point 12.1 deployment foundations are technically verified, hardened, and safe.
- **Strict Boundary Confirmation**:
  - No cloud VMs, PostgreSQL servers, or Redis instances have been provisioned.
  - No DNS records or SSL certificates have been generated.
  - No real credentials have been requested or stored.
  - No Git commits or pushes have been executed.
  - Repository execution stops here pending explicit user authorization to proceed to Point 12.2 (PostgreSQL Infrastructure & Database Staging).
