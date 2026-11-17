# HeartAI — Point 13.2B: Final Pre-Integration Hardening Report

**Date**: November 17, 2026
**Implementation Engineer**: Senior Application Security & Reliability Engineer (Antigravity Autonomous Verification System)
**Baseline Git Revision**: `c8cad27c1edb22c942847e58171e7e0025b000ce`
**Phase Objective**: Resolve the Three Operational Hardening Recommendations from the Point 13.2A Audit Prior to Git Integration
**Target Architecture**: Dedicated Ubuntu 24.04 LTS VM (FastAPI, NiceGUI, PostgreSQL 16, Redis 7, Nginx)
**Hardening Verdict**: **`ALL 3 PRE-INTEGRATION RECOMMENDATIONS RESOLVED — READY FOR GIT INTEGRATION`**
**Operating Clearance**: **INVESTIGATIONAL RESEARCH & EDUCATIONAL USE ONLY (CLINICAL DIAGNOSIS PROHIBITED)**

---

## 1. Executive Summary

Following the Point 13.2A Independent Remediation Verification, three operational hardening recommendations were prioritized for pre-integration resolution:
1. **NiceGUI Session Cookie Protection**: Explicit configuration of `session_middleware_kwargs={"https_only": True}` in staging and production to ensure the `Secure` attribute is appended to session cookies by Starlette.
2. **Reverse-Proxy IP Fallback Hardening**: Hardening `get_trusted_client_ip()` to prefer the rightmost proxy-appended IP (`parts[-1]`) in `X-Forwarded-For` when `X-Real-IP` is absent, preventing client-controlled leftmost header trust.
3. **Automated Migration Lifecycle Enforcement**: Updating `heartai-backend.service` to enforce `alembic upgrade head` via `ExecStartPre`, guaranteeing migrations run sequentially before application workers are spawned and failing fast if the database is unmigrated or unreachable.

All three enhancements were implemented and verified with zero regression to existing UI aesthetics, animations, or scientific invariants.

### Summary of Point 13.2B Hardening Actions
| Item | Component | Area | Action Taken | Verification |
| :---: | :--- | :--- | :--- | :---: |
| **1** | `motion_demo.py` | NiceGUI Session Security | Added `get_session_middleware_kwargs()` passing `{"https_only": True}` in `production`/`staging` and `{"https_only": False}` in `development`/`test`. | Unit Tests & Middleware Inspection |
| **2** | `app/core/rate_limit.py` | Reverse Proxy Anti-Spoofing | Updated `get_trusted_client_ip()` to select `parts[-1]` (rightmost proxy-appended address) instead of `parts[0]` when `X-Real-IP` is absent. Preserved socket-peer trust check. | 4 Regression Test Cases |
| **3** | `deploy/systemd/heartai-backend.service`<br>`DEPLOYMENT_GUIDE.md`<br>`deploy/scripts/provision_ubuntu24.sh` | Alembic Migration Enforcement | Added `ExecStartPre=/opt/heartai/.venv/bin/alembic upgrade head` before Gunicorn `ExecStart`. Updated documentation and provisioning scripts. | Static Unit Test & Systemd Inspection |

---

## 2. Technical Implementation Details

### 2.1 Scope 1: Secure NiceGUI Session Cookies (`motion_demo.py`)

#### Problem Analysis
NiceGUI 4.0.0 delegates session management to Starlette's `SessionMiddleware`. While Starlette sets `HttpOnly` and `SameSite=lax` by default, the `Secure` cookie flag (`https_only`) defaults to `False`. Although Nginx terminates TLS 1.3 and enforces HSTS at the perimeter, defense-in-depth requires the Python application layer to explicitly instruct browsers that the session cookie must only be transmitted over HTTPS in staging and production environments.

#### Implementation
In `motion_demo.py`:
1. **Helper Function Definition (Lines 102–114)**:
   ```python
   def get_session_middleware_kwargs() -> dict[str, Any]:
       """Resolves session cookie middleware kwargs based on environment (Point 13.2B).

       In staging and production, configures https_only=True so Starlette's SessionMiddleware
       emits the Secure flag on the session cookie. In development, https_only=False permits
       local HTTP evaluation without requiring local TLS certificates.
       Note: The session cookie contains only a cryptographically signed session ID (via
       TimestampSigner/HMAC); user data is stored server-side in NiceGUI app.storage.user.
       """
       if settings.APP_ENV in {"production", "staging"}:
           return {"https_only": True}
       return {"https_only": False}
   ```
2. **`ui.run()` Configuration (Lines 1590–1598)**:
   ```python
   if __name__ in {"__main__", "__mp_main__"}:
       ui.run(
           title="HeartAI — Advanced Motion & Aarogya Saathi Demo",
           host=settings.FRONTEND_HOST,
           port=settings.FRONTEND_PORT,
           reload=False,
           show=False,
           storage_secret=settings.SECRET_KEY,
           session_middleware_kwargs=get_session_middleware_kwargs(),
       )
   ```

#### Accurate Architectural Characterization of NiceGUI Sessions
- **Signed, Not Encrypted Cookies**: Starlette's `SessionMiddleware` utilizes `itsdangerous.TimestampSigner(str(secret_key))` over base64-encoded JSON. The cookie is **tamper-evident and signed**, but not encrypted.
- **Minimal Cookie Payload**: The cookie stores only the session identifier: `request.session['id'] = str(uuid.uuid4())`.
- **Server-Side Data Persistence**: User credentials and tokens (`access_token`, `user_email`) reside strictly on the server in NiceGUI's `app.storage.user` (stored locally in `.nicegui/storage-user-<uuid>.json` or in Redis if `NICEGUI_REDIS_URL` is configured). The client browser never receives the raw token inside the `session` cookie.

---

### 2.2 Scope 2: Reverse-Proxy IP Fallback Hardening (`app/core/rate_limit.py`)

#### Problem Analysis
Under Nginx's standard reverse proxy configuration (`proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`), client-supplied `X-Forwarded-For` headers are preserved on the left, and Nginx appends the client's direct connecting socket IP (`$remote_addr`) to the right (`<untrusted_client_header>, <real_client_ip>`).
If `X-Real-IP` were ever omitted, taking `parts[0]` would trust the leftmost client-supplied header.

#### Implementation
In `app/core/rate_limit.py` (Lines 19–46):
```python
def get_trusted_client_ip(request: Request) -> str:
    """Extracts client IP address safely, trusting forwarded headers ONLY from authorized proxies (REL-02).

    Prevents IP spoofing via crafted X-Forwarded-For or X-Real-IP headers when requests originate
    from untrusted sources. Prefers X-Real-IP (overwritten by reverse proxy) and falls back to
    the rightmost proxy-appended entry (parts[-1]) of X-Forwarded-For (Point 13.2B).
    """
    client_host = request.client.host if request.client else "127.0.0.1"

    # Parse configured trusted proxy IPs (e.g. "127.0.0.1,::1")
    trusted_proxies = {ip.strip() for ip in settings.FORWARDED_ALLOW_IPS.split(",") if ip.strip()}

    # If direct connection is NOT from a trusted reverse proxy, use socket host (disregard headers)
    if client_host not in trusted_proxies:
        return client_host

    # When connected from trusted proxy (e.g. Nginx on 127.0.0.1), inspect verified forwarded headers
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip and x_real_ip.strip():
        return x_real_ip.strip()

    # Fallback to rightmost proxy-appended address in X-Forwarded-For ($proxy_add_x_forwarded_for)
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for and x_forwarded_for.strip():
        parts = [p.strip() for p in x_forwarded_for.split(",") if p.strip()]
        if parts:
            return parts[-1]

    return client_host
```

#### Multi-Tier Spoofing Defense Matrix
| Connection Route | Socket Peer IP | Client Headers Sent | `get_trusted_client_ip()` Output | Security Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **Direct (Bypassing Nginx)** | `198.51.100.22` (Untrusted) | `X-Real-IP: 10.0.0.1`<br>`X-Forwarded-For: 10.0.0.1` | `198.51.100.22` | **PASS**: Headers disregarded; socket IP used |
| **Via Nginx (Normal)** | `127.0.0.1` (Trusted) | `X-Forwarded-For: 10.0.0.1` | `203.0.113.50` (Nginx sets `X-Real-IP: 203.0.113.50`) | **PASS**: `X-Real-IP` takes precedence |
| **Via Nginx (No X-Real-IP)** | `127.0.0.1` (Trusted) | `X-Forwarded-For: 10.0.0.1` (Nginx produces `10.0.0.1, 203.0.113.50`) | `203.0.113.50` (`parts[-1]`) | **PASS**: Rightmost appended IP selected; leftmost rejected |
| **Via Nginx (Missing Headers)** | `127.0.0.1` (Trusted) | (None) | `127.0.0.1` | **PASS**: Safe fallback to socket host |

---

### 2.3 Scope 3: Automated Systemd Alembic Pre-Start Enforcement (`deploy/systemd/heartai-backend.service`)

#### Problem Analysis
In the Point 13.1 baseline, Alembic migrations were documented as an operational step prior to service start, but the systemd unit `heartai-backend.service` launched Gunicorn directly without enforcing migration execution in systemd itself. If the service was started against an unmigrated database, the application would boot (since connection check passed), but requests to database-backed routes would fail at request time. Additionally, having multiple Gunicorn workers attempt migrations concurrently at application startup is an anti-pattern.

#### Implementation
1. **Systemd Service Unit (`deploy/systemd/heartai-backend.service`)**:
   ```ini
   [Unit]
   Description=HeartAI FastAPI Backend Service (Gunicorn + Uvicorn)
   After=network.target postgresql.service redis.service
   Wants=postgresql.service redis.service

   [Service]
   Type=notify
   User=heartai
   Group=heartai
   WorkingDirectory=/opt/heartai
   EnvironmentFile=/opt/heartai/.env
   ExecStartPre=/opt/heartai/.venv/bin/alembic upgrade head
   ExecStart=/opt/heartai/.venv/bin/gunicorn -c deploy/gunicorn.conf.py main:app
   ExecReload=/bin/kill -s HUP $MAINPID
   KillMode=mixed
   TimeoutStopSec=30
   Restart=always
   RestartSec=5s
   LimitNOFILE=65535
   ```
2. **Sequential, Fail-Closed Pre-Start Guarantees**:
   - `ExecStartPre` executes as user `heartai` within `/opt/heartai` using the virtual environment `/opt/heartai/.venv/bin/alembic` with all variables from `/opt/heartai/.env` loaded.
   - It runs strictly sequentially **once** before any Gunicorn or Uvicorn worker processes are spawned, completely avoiding concurrent migration race conditions.
   - If `alembic upgrade head` fails (e.g. database offline, connection timeout, migration conflict, or syntax error), `ExecStartPre` returns a non-zero exit code. Systemd immediately aborts the startup sequence and refuses to launch Gunicorn.
3. **Documentation & Script Synchronizations**:
   - Updated `DEPLOYMENT_GUIDE.md` (Sections 5 & 7.1) reflecting `ExecStartPre=/opt/heartai/.venv/bin/alembic upgrade head`.
   - Updated `deploy/scripts/provision_ubuntu24.sh` (Line 174) noting that while systemd enforces migrations automatically via `ExecStartPre`, running initial migrations manually confirms output.
4. **Clarification on PostgreSQL 16 Testing Boundary**:
   - Automated unit and integration tests run against ephemeral SQLite databases on the Windows workstation. Live PostgreSQL 16 migration testing will be performed on the target Ubuntu 24.04 staging instance during Point 13.2.

---

## 3. Automated Verification & Regression Testing

### 3.1 New & Updated Regression Tests (`tests/test_pre_staging_remediation.py`)
Two new test cases and updated rate limiting tests were added to validate the Point 13.2B hardening:

1. **`test_frontend_session_middleware_kwargs_environment_sensitive`**:
   - Validates that `get_session_middleware_kwargs()` returns `{"https_only": True}` in `production` and `staging`.
   - Validates that it returns `{"https_only": False}` in `development` and `test`.
2. **`test_trusted_client_ip_from_trusted_reverse_proxy_x_forwarded_for_fallback`**:
   - Validates that when `X-Real-IP` is absent and `X-Forwarded-For: 10.0.0.1, 10.0.0.2, 198.51.100.42` is received from a trusted proxy (`127.0.0.1`), `get_trusted_client_ip()` extracts the rightmost proxy-appended address `198.51.100.42` (`parts[-1]`), rejecting the spoofed client entries `10.0.0.1` and `10.0.0.2`.
3. **`test_systemd_backend_service_enforces_alembic_exec_start_pre`**:
   - Statically verifies `deploy/systemd/heartai-backend.service`:
     - Confirms `ExecStartPre=/opt/heartai/.venv/bin/alembic upgrade head` exists.
     - Confirms `ExecStartPre` appears strictly prior to `ExecStart`.
     - Confirms dependency order `After=network.target postgresql.service redis.service`.
     - Confirms execution context `User=heartai`, `WorkingDirectory=/opt/heartai`, and `EnvironmentFile=/opt/heartai/.env`.

### 3.2 Test Suite Execution Output
```
.venv\Scripts\python -m pytest tests/test_pre_staging_remediation.py -v
============================= 20 passed in 4.47s =============================
```

### 3.3 Full Test Suite Pass Rate
```
.venv\Scripts\python -m pytest -q
============================= 203 passed in 46.54s =============================
```
- **Total Test Files**: 18
- **Total Tests Collected & Passed**: 203 (100% pass rate; zero failures, zero errors, zero warnings).

### 3.4 Code Quality & Linter Compliance
```
.venv\Scripts\python -m ruff check .
All checks passed!

git diff --check
(Zero trailing whitespace, zero merge markers, clean exit code 0)
```

---

## 4. Scientific & Cryptographic Invariants Confirmation

All scientific baselines remain strictly verified and bit-identical:
- **Model Checksum (SHA-256)**: `5dc415201016ed1223fd1f4c9cb295e14b2dd64639ad507d63efb16bed51f890` (Exact Match)
- **Preprocessor Checksum (SHA-256)**: `3a354b5f6fb66bfce97bfc2ad2d92303e46d98a3e093e7069fefa213afc67055` (Exact Match)
- **Operating Decision Threshold**: `0.09` in `Settings.OPERATING_THRESHOLD`
- **Canonical Feature Schema**: Exactly 25 BRFSS survey features in `PatientBRFSSInput`
- **Symptom Isolation**: Emergency free-text symptoms strictly excluded from tabular ML pipeline
- **Scientific Framing**: Retrospective self-reported historical CVD (`_MICHD`) risk estimation; acute event prediction and autonomous clinical diagnosis disclaimed
- **Platform Framing**: Research & Educational Platform

---

## 5. Working Tree Status & Secret Hygiene

### 5.1 Modified Files Inventory (Point 13.1 & 13.2B)
1. `app/core/config.py`: Configuration hardening (`FORWARDED_ALLOW_IPS`, `ENABLE_MODEL_IMPORT`).
2. `app/core/rate_limit.py`: Anti-spoofing client IP resolution with `parts[-1]` fallback.
3. `app/db/session.py`: Database startup isolation (`create_all` skipped in staging/prod).
4. `deploy/gunicorn.conf.py`: Reverse proxy header trust alignment.
5. `deploy/systemd/heartai-backend.service`: Enforced `ExecStartPre` for Alembic migrations.
6. `deploy/scripts/restore_staging.sh`: Disaster recovery health parsing correction (`.model.loaded`, `.database.connected`).
7. `deploy/scripts/verify_staging.sh`: Verification script health parsing correction (`.model.loaded`).
8. `deploy/scripts/provision_ubuntu24.sh`: Provisioning documentation alignment.
9. `DEPLOYMENT_GUIDE.md`: Documentation synchronization for systemd and migrations.
10. `main.py`: Model sync lockdown, lifespan error handling, and research metadata.
11. `motion_demo.py`: NiceGUI `https_only` session cookies, Bearer token injection, logout state, and mock mode elimination.
12. `tests/test_pre_staging_remediation.py`: 20 regression test cases covering all remediations and hardenings.

### 5.2 Secret Hygiene Check
Exhaustive diff review confirmed zero credentials, private keys, API keys, or machine-specific tokens were introduced into the repository.

---

## 6. Final Readiness Verdict & Stop Condition

With the resolution of all three operational hardening items, the HeartAI platform is fully prepared for Git integration.

**Final Verdict: `READY FOR GIT COMMIT & CONTROLLED STAGING AUTHORIZATION`**

*Stop Condition Met*: All modifications remain clean, tested, and uncommitted in the local working directory. No infrastructure has been provisioned, no DNS configured, and no cloud costs incurred.
