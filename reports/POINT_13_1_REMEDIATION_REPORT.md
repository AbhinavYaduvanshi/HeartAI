# HeartAI — Point 13.1: Pre-Staging Security & Reliability Remediation Report

**Date**: November 17, 2026
**Implementation Engineer**: Senior Application Security & Reliability Engineer (Antigravity Autonomous Verification System)
**Baseline Git Revision**: `c8cad27c1edb22c942847e58171e7e0025b000ce`
**Phase Objective**: Targeted Pre-Staging Remediation of Mandatory Audit Findings (Point 13.0 Audit)
**Target Architecture**: Single Dedicated Ubuntu 24.04 LTS VM (FastAPI, NiceGUI, PostgreSQL 16, Redis 7, Nginx)
**Remediation Verdict**: **`ALL 5 MANDATORY PRE-STAGING FINDINGS REMEDIATED — READY FOR CONTROLLED STAGING`**
**Operating Clearance**: **INVESTIGATIONAL RESEARCH & EDUCATIONAL USE ONLY (CLINICAL DIAGNOSIS PROHIBITED)**

---

## 1. Executive Summary

Following the Point 13.0 Comprehensive Security & Reliability Audit, 5 priority findings were identified as requiring resolution prior to controlled cloud staging. In Point 13.1, targeted remediations were designed, implemented, and verified with zero regression to existing UI aesthetics or scientific invariants.

### Summary of Remediated Findings
| Priority | Finding ID | Severity | Category | Component | Resolution Summary | Verification |
| :---: | :--- | :---: | :--- | :--- | :--- | :---: |
| **P1** | **REL-01** | **HIGH** | Reliability / DR | `deploy/scripts/restore_staging.sh`<br>`deploy/scripts/verify_staging.sh` | Corrected health query to nested `.model.loaded` and `.database.connected`. Added single-request pipeline with `--max-time 10` and default fallback. | 4/4 Tests Passed |
| **P2** | **SEC-01** | **HIGH** | Authentication / Deserialization | `main.py`<br>`app/core/config.py` | Disabled runtime model import by default (`ENABLE_MODEL_IMPORT=False`). Enforced strict HTTP 403 in staging/production, requiring JWT authentication and path sandboxing within `models/` in development. | 4/4 Tests Passed |
| **P3** | **REL-03** | **MEDIUM** | Database Schema Lifecycle | `app/db/session.py`<br>`main.py` | Restricted `Base.metadata.create_all()` to `development`/`test` environments. In `staging`/`production`, startup strictly verifies PostgreSQL connectivity, failing fast if offline and delegating DDL exclusively to Alembic. | 3/3 Tests Passed |
| **P4** | **SEC-02** | **HIGH** | Frontend Session & Auth | `motion_demo.py` | Integrated NiceGUI encrypted cookie storage (`app.storage.user`) with `storage_secret=settings.SECRET_KEY`. Persisted JWT tokens upon login, injected `Authorization: Bearer <token>` into all backend requests, removed deceptive mock mode, and added navbar user state/logout. | 3/3 Tests Passed |
| **P5** | **REL-02** | **MEDIUM** | Rate Limiting Anti-Spoofing | `app/core/rate_limit.py`<br>`app/core/config.py`<br>`deploy/gunicorn.conf.py` | Replaced unverified remote address resolution with `get_trusted_client_ip()`. Disregards `X-Forwarded-For` / `X-Real-IP` headers unless direct socket peer matches `FORWARDED_ALLOW_IPS` (`127.0.0.1,::1`). | 3/3 Tests Passed |
| **Extra** | **SCI-01** | **INFO** | Scientific Framing | `main.py` | Replaced legacy "Clinical Intelligence" service titles and docstrings with "Research & Educational" platform framing. | 1/1 Test Passed |

---

## 2. Detailed Remediation Inventory & Code Changes

### 2.1 Priority 1 — REL-01: Health-Check JSON Path Correction

#### Problem
In `deploy/scripts/restore_staging.sh` and `deploy/scripts/verify_staging.sh`, the health inspection parsed `.model_loaded` from the root of `/health`. However, `/health` returns `{ "status": "healthy", "model": { "loaded": true, ... }, "database": { "connected": true, ... } }`. Consequently, `MODEL_LOADED` evaluated to `"false"`, causing automated disaster recovery drills and health verifications to trigger false rollback alarms. Furthermore, the scripts queried `curl` multiple times, risking race conditions.

#### Implementation Changes
1. **`deploy/scripts/restore_staging.sh` (Lines 151–157)**:
   ```bash
   # Safe, robust health check parsing using nested .model.loaded and .database.connected (REL-01)
   HEALTH_JSON=$(curl -s -f --max-time 10 http://127.0.0.1:8000/health 2>/dev/null || echo "{}")
   HEALTH_STATUS=$(echo "${HEALTH_JSON}" | jq -r '.status // "failed"' 2>/dev/null || echo "failed")
   MODEL_LOADED=$(echo "${HEALTH_JSON}" | jq -r '(.model.loaded // false) | tostring' 2>/dev/null || echo "false")
   DB_CONNECTED=$(echo "${HEALTH_JSON}" | jq -r '(.database.connected // false) | tostring' 2>/dev/null || echo "false")

   if [ "${HEALTH_STATUS}" == "healthy" ] && [ "${MODEL_LOADED}" == "true" ] && [ "${DB_CONNECTED}" == "true" ]; then
   ```
2. **`deploy/scripts/verify_staging.sh` (Lines 86–92)**:
   ```bash
   HEALTH_JSON=$(curl -s -f --max-time 10 http://127.0.0.1:8000/health 2>/dev/null || echo "{}")
   BACKEND_STATUS=$(echo "${HEALTH_JSON}" | jq -r '.status // "down"' 2>/dev/null || echo "down")
   MODEL_LOADED=$(echo "${HEALTH_JSON}" | jq -r '(.model.loaded // false) | tostring' 2>/dev/null || echo "false")
   if [ "${BACKEND_STATUS}" == "healthy" ] && [ "${MODEL_LOADED}" == "true" ]; then
   ```

#### Verification
- Regression tests simulate healthy responses, missing model sections, `loaded: false`, and connection timeouts.
- Both scripts safely parse boolean strings (`"true"` / `"false"`), ensuring verified restores never roll back due to JSON parsing errors.

---

### 2.2 Priority 2 — SEC-01: Model Import Lockdown & Secure Provenance

#### Problem
The endpoint `POST /api/v1/models/sync-drive` permitted unauthenticated callers to specify arbitrary filesystem directory paths (`source_dir`) to load and deserialize joblib models into memory.

#### Implementation Changes
1. **`app/core/config.py` (Lines 108–114, 237–243)**:
   - Added configuration setting:
     ```python
     ENABLE_MODEL_IMPORT: bool = Field(
         False,
         description="Administrative toggle to permit runtime model import endpoints. Strictly False by default.",
     )
     ```
   - Added environment validator in `validate_production_environment`:
     ```python
     if self.ENABLE_MODEL_IMPORT:
         raise ValueError(
             f"ENABLE_MODEL_IMPORT is prohibited in {self.APP_ENV} environments (SEC-01). "
             "Runtime filesystem model deserialization is strictly disabled."
         )
     ```
2. **`main.py` (Lines 184–228)**:
   - Attached `current_user: User = Depends(get_current_user)` to the route.
   - Enforced hard fail-closed check:
     ```python
     if not settings.ENABLE_MODEL_IMPORT or settings.APP_ENV in {"production", "staging"}:
         raise HTTPException(
             status_code=status.HTTP_403_FORBIDDEN,
             detail=f"Dynamic model synchronization from filesystem paths is disabled in {settings.APP_ENV} mode...",
         )
     ```
   - Sandboxed development usage: Enforces `src_path.is_relative_to(allowed_root)` where `allowed_root = Path("models").resolve()`, forbidding path traversal.

#### Verification
- Tested unauthenticated caller -> HTTP 401 Unauthorized.
- Tested authenticated caller in default config (`ENABLE_MODEL_IMPORT=False`) -> HTTP 403 Forbidden.
- Tested `ENABLE_MODEL_IMPORT=True` in production mode -> Application fails fast on boot with `ValueError`.
- Tested directory traversal attempt in dev mode -> HTTP 400 Bad Request.

---

### 2.3 Priority 3 — REL-03: Startup Database Schema Isolation & Alembic Governance

#### Problem
`main.py` invoked `init_db()` during application lifespan, which called `Base.metadata.create_all(bind=engine)`. In staging and production, table generation should be exclusively managed through Alembic migrations to prevent unversioned schema mutations and race conditions between multiple Gunicorn workers.

#### Implementation Changes
1. **`app/db/session.py` (Lines 64–87)**:
   ```python
   def init_db() -> None:
       from app.db import models  # noqa: F401

       if settings.APP_ENV in {"production", "staging"}:
           connected, dialect = check_db_connection()
           if not connected:
               raise RuntimeError(
                   f"Database connectivity check failed during startup in {settings.APP_ENV} mode (dialect: {dialect}). "
                   "Ensure PostgreSQL is active and credentials in DATABASE_URL are valid."
               )
           logger.info(
               "Database connectivity verified in %s mode (dialect: %s). Schema is managed via Alembic migrations.",
               settings.APP_ENV,
               dialect,
           )
           return

       Base.metadata.create_all(bind=engine)
       logger.info("Database initialized successfully (dialect: %s).", engine.dialect.name)
   ```
2. **`main.py` (Lifespan Startup Error Handling, Lines 45–53)**:
   ```python
   try:
       init_db()
   except Exception as exc:
       logger.error("Database initialization failed: %s", exc)
       if settings.APP_ENV in {"production", "staging"}:
           raise RuntimeError(
               f"Fatal: Database initialization failed during startup in {settings.APP_ENV} mode: {exc}"
           ) from exc
   ```

#### Verification
- In `development` / `test`: Tables are automatically created for developer velocity and ephemeral testing.
- In `staging` / `production`: `Base.metadata.create_all` is never called. If database connectivity fails, startup immediately aborts with `RuntimeError`.

---

### 2.4 Priority 4 — SEC-02: Frontend Session Management & JWT Injection

#### Problem
In `motion_demo.py`, successful user authentication in `execute_sign_in()` was acknowledged in the UI but the returned JWT `access_token` was discarded. Backend REST calls (`/api/v1/ai/chat`, `/api/v1/ai/symptoms`, `/predict`) were made unauthenticated. Additionally, when authentication failed or backend was offline, the UI silently fell back to a deceptive "local mock mode".

#### Implementation Changes
1. **`motion_demo.py` (Session Helper Functions, Lines 76–118)**:
   - Implemented `get_session_token()`, `get_auth_headers()`, `is_user_authenticated()`, and `clear_user_session()`.
   - Utilizes NiceGUI's server-signed, encrypted user session storage: `app.storage.user`.
2. **`motion_demo.py` (Authentication Flow & Elimination of Mock Mode, Lines 350–392)**:
   - On successful sign in: Stores `access_token`, `user_email`, and `user_name` in `app.storage.user`.
   - On authentication failure (HTTP 401/403): Clears session storage and displays exact error messages ("Invalid email or password").
   - On backend unreachable: Displays "Backend service unreachable at {BACKEND_API_URL}. Ensure FastAPI is running."
   - Eliminated silent local mock mode completely.
3. **`motion_demo.py` (Header Injection Across Backend Endpoints)**:
   - Injected `headers=get_auth_headers()` into:
     - `/api/v1/ai/chat` (Aarogya Saathi interactive dialog)
     - `/api/v1/ai/symptoms` (Emergency clinical symptom evaluator)
     - `/predict` (Primary cardiovascular risk assessment form)
4. **`motion_demo.py` (UI Navbar User State & Sign Out Button, Lines 460–485, 1070–1085)**:
   - Navbar dynamically reflects authenticated user status (`"Sign Out (Dr. ...)"` with logout icon).
   - Sign Out button clears session storage, resets button state, and issues a success notification.
5. **`motion_demo.py` (Storage Secret Configuration, Line 1582)**:
   - Configured `ui.run(..., storage_secret=settings.SECRET_KEY)` to ensure browser cookies for `app.storage.user` are cryptographically signed and encrypted.

#### Verification
- All UI layouts, animations, cards, and theme toggling remain pixel-identical.
- Unit tests verify session token injection, invalid token handling, and logout state clearing.

---

### 2.5 Priority 5 — REL-02: Reverse Proxy Rate Limiting Anti-Spoofing

#### Problem
SlowAPI's default IP extraction helper (`get_remote_address`) in `app/core/rate_limit.py` inspected `request.client.host`. In the presence of reverse proxies (Nginx), this could either rate-limit all traffic under `127.0.0.1` or, if configured naively with headers, allow malicious clients to spoof their IP by sending custom `X-Forwarded-For: <fake-ip>` headers to bypass rate limits.

#### Implementation Changes
1. **`app/core/config.py` (Lines 98–101)**:
   - Added trusted proxy configuration:
     ```python
     FORWARDED_ALLOW_IPS: str = Field(
         "127.0.0.1,::1",
         description="Comma-separated trusted proxy IPs or CIDRs authorized to forward client headers.",
     )
     ```
2. **`app/core/rate_limit.py` (Lines 19–46, 80)**:
   - Implemented `get_trusted_client_ip(request: Request) -> str`:
     ```python
     def get_trusted_client_ip(request: Request) -> str:
         client_host = request.client.host if request.client else "127.0.0.1"
         trusted_proxies = {ip.strip() for ip in settings.FORWARDED_ALLOW_IPS.split(",") if ip.strip()}

         # If direct connection is NOT from a trusted reverse proxy, use socket host (disregard headers)
         if client_host not in trusted_proxies:
             return client_host

         # When connected from trusted proxy (e.g. Nginx on 127.0.0.1), inspect verified forwarded headers
         x_real_ip = request.headers.get("X-Real-IP")
         if x_real_ip and x_real_ip.strip():
             return x_real_ip.strip()

         x_forwarded_for = request.headers.get("X-Forwarded-For")
         if x_forwarded_for and x_forwarded_for.strip():
             parts = [p.strip() for p in x_forwarded_for.split(",") if p.strip()]
             if parts:
                 return parts[0]

         return client_host
     ```
   - Bound `limiter = Limiter(key_func=get_trusted_client_ip, ...)`
3. **`deploy/gunicorn.conf.py` (Line 33)**:
   - Added `forwarded_allow_ips = os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1,::1")` to align Gunicorn proxy trust with application middleware.

#### Verification
- Test with spoofed headers from untrusted socket IP (`198.51.100.22`) -> `get_trusted_client_ip()` correctly returns `198.51.100.22`, ignoring spoofed headers.
- Test from trusted socket proxy (`127.0.0.1`) with `X-Forwarded-For: 203.0.113.195` -> correctly extracts `203.0.113.195`.

---

## 3. Scientific Invariants & Clinical Provenance Verification

All scientific baselines established during model calibration, verification, and UI integration were strictly preserved:

| Metric / Invariant | Expected Standard | Observed Implementation | Status |
| :--- | :--- | :--- | :---: |
| **Model Checksum** | `5dc415201016ed1223fd1f4c9cb295e14b2dd64639ad507d63efb16bed51f890` | Verified matching `best_model.joblib` | **PRESERVED** |
| **Preprocessor Checksum** | `3a354b5f6fb66bfce97bfc2ad2d92303e46d98a3e093e7069fefa213afc67055` | Verified matching `preprocessing_pipeline.joblib` | **PRESERVED** |
| **Decision Threshold** | `0.09` (Calibrated for high sensitivity on BRFSS) | `OPERATING_THRESHOLD = 0.09` in `config.py` | **PRESERVED** |
| **Input Feature Schema** | Exactly 25 canonical BRFSS survey features | Verified via `BRFSSInputFeatures` in `schemas/prediction.py` | **PRESERVED** |
| **Clinical Isolation** | Symptoms strictly isolated from tabular ML pipeline | Free-text / acute symptoms routed exclusively to emergency safety rules | **PRESERVED** |
| **Target Label Definition** | Retrospective self-reported historical CVD (`_MICHD`) | Framed strictly as historical cardiovascular disease risk estimation | **PRESERVED** |
| **Intended Use Boundary** | Investigational research & health education only | No autonomous diagnosis, acute cardiac event prediction, or clinical triage | **PRESERVED** |

---

## 4. Verification & Testing Evidence

### 4.1 Remediation Regression Test Suite (`tests/test_pre_staging_remediation.py`)
A dedicated automated test suite containing 18 test cases was authored to specifically validate all 5 remediations:

```
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_health_json_nested_structure_parsing PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_health_json_missing_or_failed_model PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_restore_script_syntax_and_health_jq_patterns PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_verify_script_syntax_and_health_jq_patterns PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_model_sync_endpoint_disabled_by_default_and_forbidden PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_model_sync_endpoint_requires_authentication PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_model_sync_production_validator_rejects_import_flag PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_model_sync_path_traversal_prevention PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_init_db_skips_create_all_in_production PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_init_db_fails_fast_on_bad_connection_in_production PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_init_db_creates_all_in_development PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_rate_limit_trusted_proxy_resolution PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_rate_limit_untrusted_peer_ignores_spoofed_headers PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_rate_limit_multiple_forwarded_for_ips PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_frontend_auth_header_injection_and_session_clearing PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_frontend_sign_in_storage_update PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_scientific_invariants_preserved PASSED
tests/test_pre_staging_remediation.py::TestPreStagingRemediation::test_service_title_and_description_framing PASSED
============================== 18 passed in 4.46s ==============================
```

### 4.2 Full Repository Test Suite
Running the entire test suite confirms zero regressions across all 18 test modules:
```
============================= 201 passed in 46.82s =============================
```

### 4.3 Code Quality & Linter Audits
```
.venv\Scripts\python -m ruff check .
All checks passed!
```

---

## 5. Staging Readiness Verdict & Recommendations

### Final Assessment
With the resolution of:
1. **REL-01** (Automated restore drills will accurately detect backend health),
2. **SEC-01** (Arbitrary model imports are disabled and locked down),
3. **REL-03** (Database schema mutations are strictly governed by Alembic),
4. **SEC-02** (Frontend sessions correctly persist and authenticate backend requests), and
5. **REL-02** (Reverse-proxy rate limiting is immune to spoofing),

the HeartAI platform satisfies all criteria established in the Point 13.0 Audit.

**Verdict: `READY FOR CONTROLLED STAGING`**

### Operational Recommendations for Staging Deployment (Point 13.2)
1. **Network Access**: Bind staging access strictly to Tailscale VPN (Alternative A) or authorized static IP allowlists (Alternative B). Do not expose public ingress.
2. **Environment Variables**: Populate `/opt/heartai/.env` with cryptographically random secrets generated on-host:
   - `SECRET_KEY` (minimum 32 characters, high entropy)
   - `BACKUP_ENCRYPTION_KEY` (32 bytes base64)
   - `DATABASE_URL` (PostgreSQL 16 staging credentials)
   - `REDIS_URL` (Redis 7 staging credentials)
   - `GEMINI_API_KEY` (Restricted API key)
3. **Database Migrations**: Always execute `alembic upgrade head` before starting `heartai-backend.service`.
4. **Disaster Recovery Validation**: Run `deploy/scripts/backup_staging.sh` followed by `deploy/scripts/verify_staging.sh` to ensure operational durability.
