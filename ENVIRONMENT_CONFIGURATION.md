# HeartAI Environment Configuration Guide

**Project**: HeartAI — Cardiovascular Research & Educational Platform  
**Configuration Engine**: Pydantic Settings (`pydantic-settings`)  
**Configuration File**: `.env` (loaded automatically from project root)  
**Security Level**: High (Confidential)  

---

## 1. Environment Variable Reference

The table below lists all runtime configuration parameters recognized by HeartAI:

| Variable Name | Type | Default Value | Production Recommendation | Criticality | Description |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `APP_ENV` | `string` | `development` | `production` | High | Runtime mode (`development`, `testing`, `staging`, `production`). |
| `APP_DEBUG` | `boolean` | `false` | `false` | Critical | Enables verbose tracebacks. Must be `false` in production. |
| `APP_HOST` | `string` | `0.0.0.0` | `127.0.0.1` | High | Interface to bind. Use `127.0.0.1` behind an Nginx proxy. |
| `APP_PORT` | `integer` | `8000` | `8000` | Medium | TCP port for FastAPI application server. |
| `FRONTEND_HOST` | `string` | `0.0.0.0` | `127.0.0.1` | High | Interface to bind NiceGUI frontend server. |
| `FRONTEND_PORT` | `integer` | `8080` | `8080` | Medium | TCP port for NiceGUI frontend server. |
| `BACKEND_API_URL` | `string` | `http://localhost:8000` | `https://your-domain.org` | High | Base URL used by frontend and clients to reach backend API. Forbidden to be localhost in production. |
| `SECRET_KEY` | `string` | *(None)* | Secure 32+ char token | **Critical** | Cryptographic secret for signing JWT tokens. Fails startup if absent, weak, or placeholder. |
| `SECRET_KEY_FALLBACK` | `string` | `None` | Set during rotation | High | Previous secret key accepted during seamless dual-key rotation. |
| `TELEMETRY_HMAC_KEY` | `string` | `None` | Secure 32+ char token | High | Dedicated HMAC pepper for anonymizing survey features in audit records. |
| `ALGORITHM` | `string` | `HS256` | `HS256` | Medium | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `integer` | `1440` (24h) | `1440` | Medium | Lifetime of issued JWT bearer tokens. |
| `DATABASE_URL` | `string` | User SQLite path | PostgreSQL 16 URL | **Critical** | Database connection string. Must use PostgreSQL for production multi-worker deployments. Prohibited to be SQLite in production/staging. |
| `REDIS_URL` | `string` | `None` | `redis://127.0.0.1:6379/0` | **Critical** | Redis connection URL for distributed rate limiting. Required in production/staging. |
| `CORS_ORIGINS` | `JSON list` | Localhost origins | Strict domain list | **Critical** | Allowed CORS origins. Never use `["*"]` in production/staging. |
| `RATE_LIMIT_DEFAULT` | `string` | `60/minute` | `60/minute` | Medium | Default rate limit for unauthenticated/general routes. |
| `RATE_LIMIT_AUTH` | `string` | `10/minute` | `10/minute` | High | Rate limit for `/login` and `/register` to prevent brute force. |
| `RATE_LIMIT_AI_CHAT` | `string` | `20/minute` | `20/minute` | High | Rate limit for conversational AI endpoints. |
| `RATE_LIMIT_AI_SYMPTOMS` | `string` | `15/minute` | `15/minute` | High | Rate limit for symptom triage queries. |
| `RATE_LIMIT_AI_PERSONALIZED` | `string` | `10/minute` | `10/minute` | High | Rate limit for consented personalized AI queries. |
| `MODEL_PATH` | `string` | `models/best_model.joblib` | `models/best_model.joblib` | **Critical** | Path to calibrated LogisticRegression artifact. |
| `PREPROCESSOR_PATH` | `string` | `models/preprocessing_pipeline.joblib` | `models/preprocessing_pipeline.joblib` | **Critical** | Path to fitted preprocessing transformer artifact. |
| `METADATA_PATH` | `string` | `models/model_metadata.json` | `models/model_metadata.json` | **Critical** | Path to locked metadata manifest containing SHA-256 hashes. |
| `OPERATING_THRESHOLD` | `float` | `0.09` | `0.09` | **Critical** | Screening decision boundary from Point 6.3 validation. |
| `CURRENT_CONSENT_TERMS_VERSION` | `string` | `2026.1` | `2026.1` | High | Current informed consent version required for personalization. |
| `GEMINI_API_KEY` | `string` | `None` | Google AI Studio Key | Medium | Optional API key for Google Gemini AI assistant. Safe educational fallback active when unset. |
| `GEMINI_MODEL` | `string` | `gemini-3.8-flash` | `gemini-3.8-flash` | Medium | Google Gemini model identifier. |
| `GEMINI_TIMEOUT_SECONDS` | `float` | `15.0` | `15.0` | Medium | Timeout in seconds for upstream Gemini API requests. |
| `GEMINI_MAX_OUTPUT_TOKENS` | `integer` | `1024` | `1024` | Medium | Maximum token generation budget for AI responses. |
| `GEMINI_TEMPERATURE` | `float` | `0.2` | `0.2` | Medium | Model temperature for grounded educational facts. |
| `LOG_LEVEL` | `string` | `INFO` | `INFO` | Medium | Application log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `LOG_FILE_PATH` | `string` | `logs/heartai.log` | `/var/log/heartai/heartai.log` | Medium | Absolute path for application log files. |

---

## 2. Fail-Closed Production Readiness Invariants

When `APP_ENV="production"` or `APP_ENV="staging"`, HeartAI's configuration engine enforces the following non-negotiable invariants:

1. **SQLite Prohibition**:
   - `DATABASE_URL` cannot start with `sqlite`. A PostgreSQL 16 connection string is strictly required.
2. **Redis Mandate for Rate Limiting**:
   - `REDIS_URL` cannot be empty or `None`. A valid Redis connection string is strictly required to prevent multi-worker rate limiting isolation.
3. **Debug Mode Prohibition**:
   - `APP_DEBUG` must be `false`. Detailed stack traces and debug endpoints are forbidden.
4. **Localhost URL Prohibition**:
   - `BACKEND_API_URL` cannot contain `localhost` or `127.0.0.1`. A valid production domain or reverse-proxy path must be declared.
5. **Wildcard CORS Prohibition**:
   - `CORS_ORIGINS` cannot contain `*`. Explicit authorized origin domains must be declared.
6. **Secret Strength Verification**:
   - `SECRET_KEY` must be at least 32 characters long, possess high character entropy (>= 8 unique characters), and cannot match any known placeholder pattern.

---

## 3. Database Migration Management (Alembic)

HeartAI utilizes Alembic for declarative schema versioning and database migrations.

### 3.1 Migration Configuration
- **Configuration File**: `alembic.ini`
- **Environment Script**: `alembic/env.py` (reads `DATABASE_URL` dynamically from `app.core.config.settings`).
- **Initial Schema Version**: `alembic/versions/001_initial_schema.py` (creates `users` and `prediction_records`).

### 3.2 Running Migrations
To upgrade the database to the latest schema revision:
```bash
alembic upgrade head
```

To rollback the database schema:
```bash
alembic downgrade -1     # Rollback one revision
alembic downgrade base   # Rollback all revisions
```

> [!IMPORTANT]
> Migrations do **NOT** execute automatically during application startup. This prevents accidental schema race conditions during multi-worker launches. Always run `alembic upgrade head` as a discrete deployment step.

---

## 4. Secrets Management Guidelines

1. **Never Commit Secrets to Version Control**:
   - `.gitignore` includes `.env`, `*.db`, `*.log`, and `models/*.joblib`.
   - Distribute only `deploy/.env.production.template` as a template with placeholder values.
2. **File System Permissions**:
   - On Linux production servers, restrict `.env` to the service user:
     ```bash
     chmod 600 /opt/heartai/.env
     chown heartai:heartai /opt/heartai/.env
     ```
3. **Secret Generation**:
   - Generate cryptographically secure tokens using:
     ```bash
     python3 -c "import secrets; print(secrets.token_urlsafe(32))"
     ```
