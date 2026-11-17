# HEARTAI — POINT 12.0: PRODUCTION INFRASTRUCTURE ASSESSMENT & DEPLOYMENT PLANNING

**Document Title**: Point 12.0 Production Infrastructure Assessment, Operational Gap Analysis & Deployment Preparation Plan  
**System**: HeartAI Cardiovascular Wellness & Research Intelligence Platform  
**Audit Date**: November 16, 2026  
**Auditor Roles**: Senior Software Architect, DevSecOps Engineer, Site Reliability Engineer (SRE), Healthcare Compliance Specialist  
**Phase Objective**: Assessment and planning only (**Deployment, Public Infrastructure Provisioning, and Cloud Deployment Prohibited**)  
**Audit Verdict**: **READY WITH DOCUMENTED BLOCKERS**  
**Regulatory / Operational Clearance**: **INVESTIGATIONAL RESEARCH USE ONLY (CLINICAL DIAGNOSIS PROHIBITED)**  

---

## 1. Executive Summary

HeartAI has completed Point 11 with a fully validated backend, dual-theme frontend, and 162/162 passing automated unit, integration, and security tests. Point 12.0 transitions the platform into production infrastructure assessment and deployment preparation.

This assessment evaluates the current code, configuration, and architecture against enterprise healthcare and DevSecOps requirements. The platform exhibits high software engineering maturity:
- **Calibrated ML Serving**: 25 CDC BRFSS features validated with dual-artifact SHA-256 cryptographic verification and sub-15ms pipeline latency.
- **Defensive Security Controls**: Salted Argon2id credential hashing, stateless JWT with dual-key rotation support, and PII sanitization.
- **Deterministic Emergency Interception**: Sub-millisecond pre-LLM regex triage surfacing Indian emergency hotlines (**112 / 102**) and international numbers (**911 / 999**).
- **Privacy Compliance**: Keyed HMAC-SHA256 input digests with affirmative consent gating and full data subject erasure (`DELETE /api/v1/auth/history`).

However, this assessment identifies **six critical deployment blockers** that must be resolved in future sub-phases before any production release:
1. **Unverified PostgreSQL Operation**: The SQLAlchemy engine supports PostgreSQL, but local test execution exercised SQLite exclusively. A live PostgreSQL test suite is mandatory.
2. **Missing Database Migration Framework**: Database tables are initialized via `Base.metadata.create_all()`. There is no Alembic schema versioning, making future schema alterations and rollbacks unsafe.
3. **In-Memory Rate Limiting Concurrency Risk**: SlowAPI runs on an in-memory storage URI (`memory://`). Multi-worker deployments will have isolated counters unless Redis is provisioned.
4. **Missing Production Dependencies**: Packages such as `redis` are installed in the local virtualenv but absent from `requirements.txt`.
5. **Decoupled Frontend / Backend Process Model**: The FastAPI backend (`main.py`) and NiceGUI frontend (`motion_demo.py`) currently run on separate ports (8000 and 8080) with a hardcoded `BACKEND_API_URL`, requiring reverse proxy routing and process supervision.
6. **Live Gemini Upstream Connectivity Unverified**: `GEMINI_API_KEY` remains a placeholder (`your_gemini_api_key_here`). While educational fallbacks and offline safety triage function perfectly, live LLM generation must be validated in staging using an authorized Google AI Studio key.

---

## 2. Mandatory Starting-State Verification

A thorough pre-assessment check confirmed complete repository integrity and alignment with the Point 11.3 baseline:

| Verification Metric | Target / Requirement | Observed Reality | Audit Status |
| :--- | :--- | :--- | :---: |
| **Active Git Branch** | `main` | `main` | **PASS** |
| **Local HEAD Commit** | `fbfc50784f146b5951b585f6c779a9cc7687476c` | `fbfc50784f146b5951b585f6c779a9cc7687476c` | **PASS** |
| **Remote Synchronization**| In sync with `origin/main` | Synchronized (`0 ahead, 0 behind`) | **PASS** |
| **Working Tree State** | Clean (0 modified / untracked files) | `nothing to commit, working tree clean` | **PASS** |
| **Point 10/10.1 Reports** | Preserved in repository root and `reports/` | Verified (`POINT_10_1_FINAL_VERIFICATION_REPORT.md`) | **PASS** |
| **Point 11 Acceptance** | Accepted with documented limitations | Verified (`POINT_11_FINAL_INTEGRATION_UAT_REPORT.md`) | **PASS** |
| **Pyarrow Absence** | Uninstalled from `.venv` | `Package(s) not found: pyarrow` | **PASS** |
| **Import System State** | Zero meta-path monkey-patches | Standard Python 3.12 module resolution active | **PASS** |

---

## 3. Detailed Infrastructure & Architectural Assessment

### 3.1 Application Architecture & Process Lifecycles

#### A. FastAPI Backend (`main.py`)
- **Framework & Version**: FastAPI `0.115.6` running on Python `3.12.8` via Uvicorn (ASGI).
- **Application Lifespan**: Governed by `@asynccontextmanager async def lifespan(app: FastAPI)`:
  1. *Startup Phase*:
     - Initializes logging subsystem (`logging_config.py`).
     - Invokes `init_db()` (`app/db/session.py`) executing `Base.metadata.create_all(bind=engine)`.
     - Invokes `model_service.load_artifacts()` (`app/services/model_service.py`), which loads `best_model.joblib` and `preprocessing_pipeline.joblib`, validates their SHA-256 hashes against `models/model_metadata.json`, and executes a synchronous warm-up inference.
     - Scans legacy model registry (`registry.scan()`).
  2. *Runtime Phase*: Yields ASGI application control to Uvicorn worker.
  3. *Shutdown Phase*: Logs graceful shutdown notice (`HeartAI API server shutting down.`).
- **Routing & Versioning**:
  - Root: `GET /` (operational health and legacy model introspection).
  - Telemetry: `GET /health` (`app/api/routes/health.py`), `GET /model-info` (`app/api/routes/model_info.py`).
  - ML Inference: `POST /predict` (`app/api/routes/prediction.py` - canonical 25-feature CDC BRFSS endpoint), `POST /api/v1/predict` (legacy Cleveland 13-feature baseline).
  - Identity & Security: `/api/v1/auth/*` (`app/api/routes/auth.py` - registration, login, profile, history erasure).
  - Generative AI & Triage: `/api/v1/ai/*` (`app/api/routes/ai.py` - chat, symptoms, metrics, lifestyle, limitations, personalized, status).
- **Static Asset Serving**:
  - Mounted via `app.mount("/static", StaticFiles(directory="static"), name="static")`.
  - Serves motion assets: GSAP (`static/js/gsap.min.js`), ScrollTrigger (`static/js/ScrollTrigger.min.js`), Lottie (`static/js/lottie.min.js`), and HeartAI Motion Controller (`static/js/heartai-motion.js`, `static/css/heartai-motion.css`).
- **Error Handling & Information Disclosure**:
  - Custom global exception handler intercepts all unhandled server exceptions, logging internal stack traces and returning a sanitized HTTP 500 JSON response: `{"detail": "An internal server error occurred. Telemetry has been logged."}`.
  - Zero database schemas, file paths, or C-extension tracebacks leak to HTTP clients.

#### B. NiceGUI Frontend (`motion_demo.py`)
- **Framework & Version**: NiceGUI `2.0.0+` (built on Starlette / FastAPI / Quasar / Tailwind CSS).
- **Serving Architecture**:
  - In development, launched via `ui.run(title=..., port=8080, reload=False, show=False)`.
  - Hosts the complete unified user experience:
    1. Navigation bar with theme toggle, active links, and mobile slide-in drawer.
    2. Physician & Researcher authentication modal.
    3. CDC BRFSS cardiovascular risk assessment modal with affirmative research consent checkbox.
    4. Aarogya Saathi (आरोग्य साथी) AI assistant floating orb and purple glassmorphic chat modal.
    5. Cardiovascular symptom triage modal with Indian emergency hotlines.
    6. Telemetry dashboard featuring isoelectric ECG SVG monitor and anatomical heart animation.
- **Architectural Coupling Gap**:
  - `motion_demo.py` line 60 hardcodes: `BACKEND_API_URL = "http://localhost:8000"`.
  - In production, running two distinct web server processes (`8000` for FastAPI and `8080` for NiceGUI) complicates process management and exposes internal ports.
  - **Remedy**: Mount NiceGUI directly into FastAPI or place both behind Nginx reverse proxy routing (e.g. `/api/*` -> FastAPI, `/*` -> NiceGUI).

---

### 3.2 Database Infrastructure

| Component | Implemented State | Production Requirement | Audit Status |
| :--- | :--- | :--- | :---: |
| **Dialect Tested** | SQLite 3 (`heartai.db` in user directory) | PostgreSQL 15+ Enterprise | **UNTESTED (PostgreSQL)** |
| **Engine Construction** | SQLAlchemy 2.0 `create_engine` | Managed Connection Pool | **PARTIALLY VERIFIED** |
| **Pool Sizing** | SQLite: Single connection; PG: pool=10, max_overflow=20 | Rightsized based on worker count | **PARTIALLY VERIFIED** |
| **Stale Connection Handling** | `pool_pre_ping=True`, `pool_recycle=1800` | Verified against idle dropouts | **VERIFIED** |
| **Schema Management** | `Base.metadata.create_all(bind=engine)` | Alembic Migration Scripts | **NOT IMPLEMENTED** |
| **Transaction Lifecycle** | Explicit session management in dependencies | Atomicity & Savepoints | **VERIFIED** |
| **Data Retention** | Audit records stored only with consent | GDPR / DPDP compliance | **VERIFIED** |

#### Critical Database Gaps & Required Actions
1. **Lack of Migration Management (Alembic)**:
   - `Base.metadata.create_all()` creates missing tables but cannot alter columns, add indexes, or manage rollbacks.
   - *Required Action*: Initialize Alembic (`alembic init alembic`), generate baseline migration revision `001_initial_schema.py`, and test upgrades/downgrades on PostgreSQL.
2. **PostgreSQL Local Testing Absence**:
   - The SQLAlchemy PostgreSQL configuration block (`app/db/session.py` lines 25-28) has never been executed in CI or local automated test suites.
   - *Required Action*: Stand up a local or CI PostgreSQL 15/16 container and execute `pytest` with `DATABASE_URL=postgresql://...`.
3. **Data Subject Erasure (`DELETE /api/v1/auth/history`)**:
   - Verified in UAT Journey E: successfully purges user prediction records via `cascade="all, delete-orphan"`.
   - *Production Requirement*: Ensure backup snapshots do not permanently preserve revoked personal data beyond defined regulatory retention horizons.

---

### 3.3 Authentication & Application Security

#### A. Password Security & Credential Hashing
- **Algorithm**: Argon2id via `argon2-cffi` (`app/core/security.py`).
- **Parameters**: `time_cost=2`, `memory_cost=65536` (64 MB), `parallelism=1`, `hash_len=32`, `salt_len=16`.
- **Timing Attack Resistance**: If a requested user email does not exist in `users`, `verify_password` executes a dummy Argon2 verification against a pre-computed constant hash, preventing username enumeration through response latency discrepancies.

#### B. JSON Web Tokens (JWT) & Secret Management
- **Token Format**: Signed JWT (`HS256`) containing `sub` (user email), `type="access"`, `iat`, and `exp`.
- **Expiration**: Defaults to 1440 minutes (24 hours).
- **Dual-Key Seamless Rotation**:
  - `app/core/security.py` checks `settings.SECRET_KEY` first.
  - If validation fails, it attempts verification against `settings.SECRET_KEY_FALLBACK`.
  - Enables zero-downtime key rotation without invalidating active sessions.
- **Fail-Closed Secret Validation**:
  - `app/core/config.py` enforces a minimum length of 32 characters, entropy requirements (>= 8 unique characters), and explicitly rejects placeholder strings.

#### C. Cross-Origin Resource Sharing (CORS)
- **Current Defaults**: `["http://localhost:8000", "http://localhost:8080", "http://127.0.0.1:8000", "http://127.0.0.1:8080"]`.
- **Production Guard**: `app/core/config.py` lines 180-188 prohibit `*` wildcard when `APP_ENV="production"`, raising an immediate configuration error.

#### D. Rate Limiting Architecture
- **Engine**: SlowAPI (`limits` library under the hood).
- **Endpoints Protected**:
  - General routes: `60/minute`
  - Authentication (`/login`, `/register`): `10/minute`
  - Conversational AI (`/ai/chat`): `20/minute`
  - Symptom triage (`/ai/symptoms`): `15/minute`
  - Personalized AI (`/ai/personalized`): `10/minute`
- **Concurrency Gap**: In-memory storage (`memory://`) is isolated per worker process.
  - *Required Action*: In production multi-worker environments, `REDIS_URL` must be configured (e.g. `redis://localhost:6379/0`) and `redis` added to `requirements.txt`.

---

### 3.4 Google Gemini AI Integration

- **SDK**: Official `google-genai` Python SDK (`app/ai/gemini_client.py`).
- **Configured Model**: `gemini-3.8-flash`.
- **Operating Status**: **NOT VERIFIED (Unconfigured API Key)**.
  - The local `.env` contains placeholder: `GEMINI_API_KEY=your_gemini_api_key_here`.
- **Graceful Fallback Mode**:
  - `app/ai/gemini_client.py` detects placeholders and unconfigured states, raising `GeminiConfigError`.
  - The AI assistant intercepts this error, serving pre-compiled educational health guidance with emergency notices.
  - Telemetry endpoint `GET /api/v1/ai/status` returns HTTP 200 with `configured: false` and actionable Google AI Studio authorization documentation.
- **Safety & Guardrails**:
  1. *Deterministic Pre-LLM Emergency Screening*: `detect_emergency_symptoms()` in `app/ai/safety.py` detects acute chest pain, radiation, dyspnea, or collapse in sub-millisecond time, returning emergency hotlines (**112 / 102 India**, 911 international) and completely bypassing Gemini.
  2. *PII Sanitization*: `sanitize_user_input()` scrubs SSNs, Aadhaar-style numbers, emails, cards, and phone numbers before generation.
  3. *Consent Enforcement*: `verify_trusted_user_consent()` verifies affirmative consent in the database before generating personalized recommendations.

---

## 4. Scientific & Medical Safety Invariants

Throughout all production planning and infrastructure phases, the following invariants are **STRICTLY LOCKED**:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    HEARTAI SCIENTIFIC & SAFETY INVARIANTS                    │
├───────────────────────────────┬──────────────────────────────────────────────┤
│ Model Artifact Checksum       │ SHA-256: 5dc415201016ed1223fd1f4c9cb295e14b2 │
│                               │          dd64639ad507d63efb16bed51f890       │
├───────────────────────────────┼──────────────────────────────────────────────┤
│ Preprocessor Artifact Checksum│ SHA-256: 3a354b5f6fb66bfce97bfc2ad2d92303e46 │
│                               │          d98a3e093e7069fefa213afc67055       │
├───────────────────────────────┼──────────────────────────────────────────────┤
│ Operating Decision Threshold  │ T = 0.09 (Optimized for screening recall)    │
├───────────────────────────────┼──────────────────────────────────────────────┤
│ Canonical Input Schema        │ Exactly 25 validated CDC BRFSS 2023 features │
├───────────────────────────────┼──────────────────────────────────────────────┤
│ Acute Symptom Isolation       │ Strictly isolated from ML inference inputs   │
├───────────────────────────────┼──────────────────────────────────────────────┤
│ Clinical Clearance Status     │ Investigational Research Use Only (No Dx)    │
├───────────────────────────────┼──────────────────────────────────────────────┤
│ Emergency Hotlines Displayed  │ 112 (National) / 102 (Ambulance) in India    │
└───────────────────────────────┴──────────────────────────────────────────────┘
```

---

## 5. Deployment Readiness Matrix

| Domain | Current Implementation | Readiness | Evidence | Gap | Required Action |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **FastAPI Backend** | Lifespan context, Uvicorn ASGI, modular routes | **VERIFIED** | `main.py`, 162/162 pytest passing | Needs production WSGI/ASGI supervisor config | Configure Gunicorn process manager with Uvicorn workers |
| **NiceGUI Frontend** | Standalone process on port 8080 | **PARTIALLY VERIFIED** | `motion_demo.py`, 9 browser screenshots | Hardcoded backend URL (`localhost:8000`); separate port | Configure Nginx reverse proxy routing to unify frontend/backend |
| **ML Inference Pipeline** | Calibrated LogisticRegression (T=0.09) | **VERIFIED** | SHA-256 match, 2.39ms classifier latency | None (Fully validated) | Lock artifact paths and file permissions in production |
| **Database Engine** | SQLite 3 (`heartai.db`) | **PARTIALLY VERIFIED** | Verified locally; PG code present | PostgreSQL has never been tested in this repository | Stand up PostgreSQL container and execute full test suite |
| **Database Migrations** | `Base.metadata.create_all()` | **NOT IMPLEMENTED** | `alembic.ini` absent | No schema versioning or rollback capability | Initialize Alembic and create baseline migration |
| **Authentication & RBAC** | Argon2id + JWT HS256 + rotation | **VERIFIED** | `app/core/security.py`, 19 security tests | Long default token expiry (24h) | Review token lifespan; implement refresh token if needed |
| **Rate Limiting** | SlowAPI (memory default) | **PARTIALLY VERIFIED** | Tested in single process | Memory backend fails in multi-worker Gunicorn | Provision Redis service and configure `REDIS_URL` |
| **Dependencies** | `requirements.txt` | **PARTIALLY VERIFIED** | Verified with pip | `redis` package missing from `requirements.txt` | Add `redis>=5.0.0` to `requirements.txt` |
| **Gemini Generative AI** | `gemini-3.8-flash` via `google-genai` | **NOT VERIFIED** | Fallback verified; placeholder key in `.env` | Upstream live connectivity unverified | Execute controlled staging test with active API key |
| **Emergency Triage** | Sub-ms regex screening (112/102) | **VERIFIED** | `app/ai/safety.py`, UAT Journey C | None | Maintain deterministic pre-LLM execution |
| **Privacy & Consent** | HMAC input digest, zero unconsented DB writes | **VERIFIED** | `app/services/prediction_service.py` | None | Ensure HMAC pepper is securely injected from environment |
| **Reverse Proxy & TLS** | Plain HTTP local execution | **NOT IMPLEMENTED** | Documented in `DEPLOYMENT_GUIDE.md` | TLS termination, HSTS, security headers not active | Provision Nginx reverse proxy with TLS 1.3 certificate |
| **Process Supervision** | Terminal commands / background tasks | **NOT IMPLEMENTED** | Documented in `DEPLOYMENT_GUIDE.md` | No auto-restart or daemon management | Create Systemd unit files (`heartai.service`) |
| **Backup & Recovery** | Documented in `BACKUP_AND_RECOVERY.md` | **NOT IMPLEMENTED** | Script documented, not scheduled | Automated backup script not active | Schedule cron backup script with GPG encryption |
| **Cloud Infrastructure** | None (Local machine only) | **REQUIRES DECISION** | Documented options | Cloud provider not yet selected | Select target cloud VM or container hosting provider |

---

## 6. Comprehensive Risk Register

| Risk ID | Description | Severity | Likelihood | Operational Impact | Repository Evidence | Mitigation Strategy | Blocks Deployment? |
| :---: | :--- | :---: | :---: | :--- | :--- | :--- | :---: |
| **RSK-01** | **PostgreSQL Untested Runtime** | High | High | Potential dialect syntax errors, type mismatches, or pool exhaustion under load. | `app/db/session.py` has PG code, but all 162 tests ran on SQLite. | Provision PostgreSQL 15+ instance, execute test suite, and validate connection pooling. | **YES** |
| **RSK-02** | **Lack of Database Migrations** | High | High | Inability to deploy schema updates or rollback failed migrations safely. | `alembic.ini` and `alembic/` do not exist. | Initialize Alembic, generate initial migration revision, and integrate into deployment pipeline. | **YES** |
| **RSK-03** | **Missing `redis` Dependency** | High | Medium | Multi-worker SlowAPI crashes or falls back to in-memory limits if `REDIS_URL` is set without the driver. | `requirements.txt` lacks `redis` package. | Add `redis>=5.0.0` to `requirements.txt` and lock versions. | **YES** |
| **RSK-04** | **In-Memory Rate Limiting Concurrency** | Medium | High | Clients can multiply rate limits across worker processes, risking API flooding. | `app/core/rate_limit.py` defaults to `memory://`. | Mandate `REDIS_URL` configuration in production deployment checks. | **YES** |
| **RSK-05** | **Live Gemini API Connectivity Unverified** | Medium | High | LLM failures, quota exhaustion, or authentication rejections upon initial launch. | `GEMINI_API_KEY` is a placeholder; status is `NOT VERIFIED`. | Execute controlled staging validation test using an authorized Google AI Studio key. | **YES** |
| **RSK-06** | **Decoupled Frontend / Backend Ports** | Medium | High | Cross-origin network blocks, hardcoded localhost URLs failing in production. | `motion_demo.py` line 60 hardcodes `BACKEND_API_URL = "http://localhost:8000"`. | Route via Nginx reverse proxy using relative paths (`/api/*` and `/*`). | **YES** |
| **RSK-07** | **Absence of TLS & Security Headers** | High | High | Data interception, man-in-the-middle attacks, clickjacking, and session theft. | Application currently binds to plain HTTP (`0.0.0.0:8000`). | Mandate Nginx reverse proxy with TLS 1.3, HSTS, CSP, and X-Frame-Options. | **YES** |
| **RSK-08** | **Unvalidated Backup & Restore Procedure** | High | Medium | Data loss in case of hardware or volume corruption. | `BACKUP_AND_RECOVERY.md` exists, but automated cron script is not active. | Implement and test automated `pg_dump` and restore verification in staging. | **YES** |
| **RSK-09** | **Cryptographic Secret Leakage** | Critical | Low | Compromise of user authentication and HMAC audit integrity. | `.gitignore` covers `.env`, but production secrets must be managed securely. | Use Linux file permissions (`chmod 600`) or cloud secret manager; forbid committed secrets. | **NO (Mitigated by validation)** |
| **RSK-10** | **Misleading Clinical Representation** | Critical | Low | Legal liability, regulatory sanctions, and clinical misuse. | Model disclaimers active across all endpoints. | Preserve investigational research-use-only boundary and emergency 112/102 guidance. | **NO (Mitigated by design)** |

---

## 7. Recommended Production Runtime Architecture

To avoid cloud vendor lock-in while providing robust reliability, a **Dedicated Linux Virtual Machine (or Containerized Linux Instance)** architecture is recommended:

```
                                  Internet
                                     │
                                     ▼ HTTPS (Port 443 / TLS 1.3)
                    ┌─────────────────────────────────┐
                    │       Nginx Reverse Proxy       │
                    │  • TLS Termination (Certbot/SSL)│
                    │  • Security Headers (HSTS, CSP) │
                    │  • Static Asset Cache (/static) │
                    │  • Gzip / Brotli Compression    │
                    └────────┬───────────────┬────────┘
                             │               │
            /api/*, /predict │               │ /* (UI Pages & WebSockets)
            /health, /docs   │               │
                             ▼               ▼
                    ┌────────────────┐ ┌────────────────┐
                    │ Gunicorn Master│ │ NiceGUI Engine │
                    │ (Uvicorn Async)│ │ (Port 8080)    │
                    │ • Worker 1     │ │ • Web Interface│
                    │ • Worker 2     │ │ • Aarogya Saathi│
                    │ • Worker N     │ │ • Interactive  │
                    │ (Unix Socket)  │ │   Widgets      │
                    └────────┬───────┘ └───────┬────────┘
                             │                 │
                             ├─────────────────┘
                             │
                             ▼
              ┌───────────────────────────────┐
              │      Data & Storage Layer     │
              │                               │
              │  ┌─────────────────────────┐  │
              │  │ PostgreSQL 15+ Database │  │
              │  │ • User Accounts         │  │
              │  │ • Consented Audit Logs  │  │
              │  └─────────────────────────┘  │
              │                               │
              │  ┌─────────────────────────┐  │
              │  │ Redis 7+ Cache          │  │
              │  │ • Distributed SlowAPI   │  │
              │  │ • Shared Worker Limits  │  │
              │  └─────────────────────────┘  │
              └───────────────────────────────┘
```

### Key Architectural Decisions
1. **Process Supervision**: Systemd service units (`heartai-backend.service`, `heartai-frontend.service`) providing automatic restart on failure, resource limits, and journald logging.
2. **Reverse Proxying**: Nginx acts as the single public entry point, mapping `/api/*`, `/predict`, `/health`, and `/model-info` to the FastAPI backend, and all UI traffic (`/`) to NiceGUI.
3. **Database Isolation**: PostgreSQL configured locally or via managed private network; listening only on internal interfaces.
4. **Cache & Rate Limiting**: Redis instance dedicated to SlowAPI token bucket storage.

---

## 8. Backup and Disaster Recovery Specification

### 8.1 Proposed Recovery Objectives (Marked for Approval)
- **Recovery Point Objective (RPO)**: **< 1 hour** (Maximum permissible data loss in disaster scenario).
- **Recovery Time Objective (RTO)**: **< 30 minutes** (Maximum permissible downtime to restore service).
*Note: These objectives are proposed targets and require formal stakeholder approval before Point 12.1.*

### 8.2 Backup Assets & Rotation Policy
1. **Stateful Database**: Full `pg_dump` executed nightly at 02:00 UTC; continuous WAL archiving enabled for point-in-time recovery.
2. **Model Artifacts & Checksums**: Immutable archive of `models/best_model.joblib`, `models/preprocessing_pipeline.joblib`, and `models/model_metadata.json`.
3. **Configuration & Secrets**: Encrypted snapshot of `.env` using GPG with symmetric or public-key encryption.
4. **Retention Schedule (GFS)**:
   - Daily backups: 14 days retention.
   - Weekly snapshots: 8 weeks retention.
   - Monthly archives: 12 months retention.

---

## 9. Phased Deployment Preparation Roadmap

The following sequential roadmap is proposed for Point 12 implementation sub-phases. **Execution of these phases is deferred until explicit authorization is granted**:

```
Point 12.0: Assessment & Planning (COMPLETED HERE)
    │
    ▼
Point 12.1: Environment & Dependency Hardening
    │  • Add `redis` to requirements.txt
    │  • Create `.env.production.template`
    │  • Configure environment validation scripts
    │
    ▼
Point 12.2: Database Migration & PostgreSQL Validation
    │  • Initialize Alembic (`alembic init alembic`)
    │  • Author baseline migration (`001_initial_schema.py`)
    │  • Execute automated test suite against live PostgreSQL instance
    │
    ▼
Point 12.3: Distributed Rate Limiting & Redis Integration
    │  • Validate SlowAPI with live Redis connection
    │  • Test multi-worker rate limiting synchronization
    │
    ▼
Point 12.4: Controlled Gemini Staging Connectivity
    │  • Configure authorized Google AI Studio staging key
    │  • Verify live generative responses and token budget limits
    │  • Validate rate-limit backoff under simulated 429 errors
    │
    ▼
Point 12.5: Reverse Proxy, Process Supervision & Frontend Unification
    │  • Author Nginx configuration (TLS 1.3, HSTS, reverse proxy routing)
    │  • Author Systemd unit service files
    │  • Resolve frontend `BACKEND_API_URL` relative routing
    │
    ▼
Point 12.6: Backup, Restore & Operational Telemetry Validation
    │  • Implement and test automated `backup.sh` script
    │  • Perform simulated disaster recovery drill on PostgreSQL
    │  • Validate log rotation and PII masking
    │
    ▼
Point 12.7: Staging Integration & Pre-Release Acceptance Audit
    │  • Execute complete 6-journey UAT in staging environment
    │  • Independent DevSecOps security scan
    │
    ▼
Point 12.8: Final Release Authorization (Go / No-Go Decision)
```

---

## 10. Explicit Unresolved Decisions Requiring User Approval

Before proceeding with infrastructure implementation, the following decisions require formal stakeholder review:

1. **Hosting Model Decision**:
   - *Option A*: Single Dedicated Linux VM (e.g. Ubuntu 24.04 LTS running Nginx, Systemd, Gunicorn, PostgreSQL, and Redis). Lowest complexity, predictable cost.
   - *Option B*: Containerized Docker Compose Stack. High portability, reproducible across cloud providers.
   - *Option C*: Managed Cloud Services (e.g. AWS ECS/RDS, GCP Cloud Run/Cloud SQL). Higher operational isolation, variable usage-based costs.
   - *Recommendation*: **Option A or Option B** for research prototype deployment.
2. **PostgreSQL Version & Host**:
   - Confirm target PostgreSQL version (recommended: **PostgreSQL 16**).
3. **Disaster Recovery Target Approval**:
   - Formally approve or adjust the proposed **RPO (< 1 hour)** and **RTO (< 30 minutes)** targets.
4. **Staging Gemini API Key Authorization**:
   - Confirm readiness to provide an active Google AI Studio key during Point 12.4 staging testing.

---

## 11. Final Assessment Verdict & Stopping Rule

### Final Verdict: **READY WITH DOCUMENTED BLOCKERS**

HeartAI is architecturally sound and code-complete for release preparation. However, deployment is blocked until the six identified operational blockers (PostgreSQL validation, Alembic migrations, Redis dependency, frontend URL unification, reverse proxy TLS, and live Gemini staging verification) are executed through the proposed phased roadmap.

### Stopping Condition Acknowledged:
- **No public infrastructure has been provisioned.**
- **No application endpoints have been deployed or exposed publicly.**
- **No cloud provider accounts or paid services have been authorized.**
- **Model artifacts, thresholds, and 25-feature schemas remain completely untouched.**
- **Execution is HALTED at the Point 12.0 assessment boundary.**
