# HeartAI Environment Configuration Guide

**Project**: HeartAI — Cardiovascular Clinical Intelligence Platform  
**Configuration Engine**: Pydantic Settings (`pydantic-settings`)  
**Configuration File**: `.env` (loaded automatically from project root)  
**Security Level**: High (Confidential)  

---

## 1. Environment Variable Reference

The table below lists all runtime configuration parameters recognized by HeartAI:

| Variable Name | Type | Default Value | Production Recommendation | Criticality | Description |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `APP_ENV` | `string` | `development` | `production` | High | Runtime mode (`development`, `staging`, `production`). |
| `APP_DEBUG` | `boolean` | `false` | `false` | Critical | Enables verbose tracebacks. Must be `false` in production. |
| `APP_HOST` | `string` | `0.0.0.0` | `127.0.0.1` | High | Interface to bind. Use `127.0.0.1` behind an Nginx proxy. |
| `APP_PORT` | `integer` | `8000` | `8000` | Medium | TCP port for application server. |
| `SECRET_KEY` | `string` | *(None)* | Secure 32+ char token | **Critical** | Cryptographic secret for signing JWT tokens. Fails startup if absent or weak. |
| `SECRET_KEY_FALLBACK` | `string` | `None` | Set during rotation | High | Previous secret key accepted during seamless dual-key rotation. |
| `TELEMETRY_HMAC_KEY` | `string` | `None` | Secure 32+ char token | High | Dedicated HMAC pepper for anonymizing survey features in audit records. |
| `ALGORITHM` | `string` | `HS256` | `HS256` | Medium | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `integer` | `1440` (24h) | `1440` | Medium | Lifetime of issued JWT bearer tokens. |
| `DATABASE_URL` | `string` | User SQLite path | PostgreSQL URL | **Critical** | Database connection string. Must use PostgreSQL for production multi-worker deployments. |
| `REDIS_URL` | `string` | `None` | `redis://localhost:6379/0` | High | Redis connection URL for distributed rate limiting across workers. |
| `CORS_ORIGINS` | `JSON list` | Localhost origins | Strict domain list | **Critical** | Allowed CORS origins. Never use `["*"]` in production. |
| `RATE_LIMIT_DEFAULT` | `string` | `60/minute` | `60/minute` | Medium | Default rate limit for unauthenticated/general routes. |
| `RATE_LIMIT_AUTH` | `string` | `10/minute` | `10/minute` | High | Rate limit for `/login` and `/register` to prevent brute force. |
| `RATE_LIMIT_AI_CHAT` | `string` | `20/minute` | `20/minute` | High | Rate limit for conversational AI endpoints. |
| `RATE_LIMIT_AI_SYMPTOMS` | `string` | `15/minute` | `15/minute` | High | Rate limit for symptom triage queries. |
| `RATE_LIMIT_AI_PERSONALIZED` | `string` | `10/minute` | `10/minute` | High | Rate limit for consented personalized AI queries. |
| `MODEL_PATH` | `string` | `models/best_model.joblib` | `models/best_model.joblib` | **Critical** | Path to calibrated LogisticRegression artifact. |
| `PREPROCESSOR_PATH` | `string` | `models/preprocessing_pipeline.joblib` | `models/preprocessing_pipeline.joblib` | **Critical** | Path to fitted preprocessing transformer artifact. |
| `METADATA_PATH` | `string` | `models/model_metadata.json` | `models/model_metadata.json` | **Critical** | Path to locked metadata manifest containing SHA-256 hashes. |
| `OPERATING_THRESHOLD` | `float` | `0.09` | `0.09` | **Critical** | Clinical screening decision boundary from Point 6.3 validation. |
| `CURRENT_CONSENT_TERMS_VERSION` | `string` | `2026.1` | `2026.1` | High | Current informed consent version required for personalization. |
| `GEMINI_API_KEY` | `string` | `None` | Google AI Studio Key | High | API key for Google Gemini generative AI assistant. |
| `GEMINI_MODEL` | `string` | `gemini-3.8-flash` | `gemini-3.8-flash` | Medium | Google Gemini model identifier. |
| `GEMINI_TIMEOUT_SECONDS` | `float` | `15.0` | `15.0` | Medium | Timeout in seconds for upstream Gemini API requests. |
| `GEMINI_MAX_OUTPUT_TOKENS` | `integer` | `1024` | `1024` | Medium | Maximum token generation budget for AI responses. |
| `GEMINI_TEMPERATURE` | `float` | `0.2` | `0.2` | Medium | Model temperature (low temperature ensures grounded educational facts). |
| `LOG_LEVEL` | `string` | `INFO` | `INFO` | Medium | Application log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `LOG_FILE_PATH` | `string` | `logs/heartai.log` | `/var/log/heartai/heartai.log` | Medium | Absolute path for application log files. |

---

## 2. Secrets Management Guidelines

1. **Never Commit Secrets to Version Control**:
   - The `.gitignore` file includes `.env`, `*.db`, `*.log`, and `models/*.joblib`.
   - Always distribute `.env.example` as a template with placeholder values.
2. **File System Permissions**:
   - On Linux production servers, restrict `.env` to the service user:
     ```bash
     chmod 600 /opt/heartai/.env
     chown heartai:heartai /opt/heartai/.env
     ```
3. **Cloud Secret Managers**:
   - In cloud environments (Google Cloud Secret Manager, AWS Secrets Manager, HashiCorp Vault), inject configuration into environment variables at container or service startup.

---

## 3. Database Connection Configuration

### SQLite (Local Development & Testing Only)
```ini
# Safe user-directory SQLite path (avoids Windows controlled folder access locks)
DATABASE_URL=sqlite:///./heartai.db
```

### PostgreSQL (Production & Staging)
```ini
# Standard connection URI
DATABASE_URL=postgresql://heartai_user:SecurePassword123@localhost:5432/heartai_db

# Connection Pool Defaults (Automatically applied by app/db/session.py):
# - pool_size: 10
# - max_overflow: 20
# - pool_recycle: 1800 (reconnect every 30 minutes)
# - pool_pre_ping: true (detect stale dropped connections)
```

---

## 4. Google Gemini AI API Configuration

1. **Obtaining an API Key**:
   - Visit [Google AI Studio](https://aistudio.google.com/) and create a project API key.
2. **Configuring the Key**:
   - Set `GEMINI_API_KEY=AIzaSy...` in your `.env`.
3. **Graceful Degradation When Key is Unset**:
   - If `GEMINI_API_KEY` is not configured or left as a placeholder, HeartAI continues operating normally for ML risk prediction and static health endpoints.
   - The `/api/v1/ai/status` endpoint will report `configured: false`, providing instructions on how to authorize access, and AI endpoints will return safe fallback educational guidance.
