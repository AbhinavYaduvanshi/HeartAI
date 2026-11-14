# HeartAI Security Operations & DevSecOps Manual

**Project**: HeartAI — Cardiovascular Clinical Intelligence Platform  
**Target Audience**: Security Engineers, DevSecOps Leads, Systems Administrators, Clinical Data Stewards  
**Classification**: Internal Operations Manual  
**Version**: 2.1.0  
**Effective Date**: November 14, 2026  

---

## 1. Threat Modeling (STRIDE Analysis)

HeartAI processes user authentication credentials, demographic/behavioral cardiovascular survey features, and generative health inquiries. The following threat matrix outlines our primary threat models and counter-measures:

| STRIDE Threat Category | Potential Vector | Implemented Countermeasure | Verification Test |
| :--- | :--- | :--- | :--- |
| **Spoofing** | Forged JWT access tokens; fake credentials | High-entropy Argon2id password hashing; HMAC-SHA256 JWT tokens with strict secret entropy (>32 chars). | `tests/test_security_hardening.py` |
| **Tampering** | Model artifact tampering; pipeline modification | Dual-artifact SHA-256 verification against locked metadata JSON during service startup; fail-closed execution. | `tests/test_production_readiness.py` |
| **Repudiation** | Denial of consent grant or revocation | Database audit trail (`consent_given`, `consent_terms_version`, `consent_updated_at`, `consent_revoked`). | `tests/test_backend_integration.py` |
| **Information Disclosure** | PII leakage via LLM prompts; secrets exposed in logs | Deterministic regex scrubbing of SSNs, emails, cards, and phone numbers; strict log masking via `sanitize_for_logging`. | `tests/test_ai_complete_experience.py` |
| **Denial of Service** | API flooding; Gemini API budget depletion | Multi-tier rate limiting via SlowAPI (Redis backend for multi-worker); prompt size caps; token output limits. | `tests/test_backend_integration.py` |
| **Elevation of Privilege** | Client asserts `user_consent_given=True` without DB record | Strict database verification (`verify_trusted_user_consent`); client-side booleans are never trusted for personalized guidance. | `tests/test_ai_complete_experience.py` |

---

## 2. Cryptographic Secret Management & Key Rotation

### 2.1 Secret Key Generation
HeartAI enforces that `SECRET_KEY` is never left empty, weak, or set to committed placeholder defaults. Every environment must generate an independent, cryptographically secure key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2.2 Dual-Key Rotation Procedure (Zero Downtime)
When rotating the master JWT secret key in production without logging out active researchers:

1. **Step 1 (Generate New Secret)**: Generate a new 32+ character key (`NEW_SECRET_KEY`).
2. **Step 2 (Configure Fallback)**: In `/opt/heartai/.env`, set:
   ```ini
   SECRET_KEY=NEW_SECRET_KEY
   SECRET_KEY_FALLBACK=OLD_SECRET_KEY
   ```
3. **Step 3 (Reload Service)**: Execute `sudo systemctl reload heartai.service`.
   - All newly issued tokens will be signed with `NEW_SECRET_KEY`.
   - Tokens previously signed with `OLD_SECRET_KEY` will continue to be validated via `SECRET_KEY_FALLBACK`.
4. **Step 4 (Retire Old Key)**: After the token expiration window (e.g., 24 hours), remove `SECRET_KEY_FALLBACK` and reload the service:
   ```ini
   SECRET_KEY=NEW_SECRET_KEY
   # SECRET_KEY_FALLBACK removed
   ```

---

## 3. Medical Safety & Emergency Triage Protocol

### 3.1 Deterministic Pre-LLM Emergency Interception
Because generative Large Language Models exhibit non-deterministic latency and potential hallucinations, acute emergency symptoms are screened **deterministically prior to invoking the Gemini API**.

- **Detection Function**: `detect_emergency_symptoms(text: str)` in `app/ai/safety.py`.
- **Latency**: Sub-millisecond (zero LLM wait).
- **Trigger Patterns**: Crushing chest pain, elephant sitting on chest, pain radiating to left arm/jaw, severe breathlessness, sudden speech slurring, facial droop, syncope, and cold sweats with chest pain.
- **Routing**: If triggered, Gemini is completely bypassed and `EMERGENCY_ALERT_MESSAGE` is returned immediately.

### 3.2 Prominent Emergency Hotline Standards
Emergency messages must prominently display national and international dispatch numbers:
- **India**: `112 (National Emergency Number) / 102 (Ambulance)`
- **US / Canada**: `911`
- **United Kingdom**: `999`
- **Europe**: `112`

---

## 4. Personally Identifiable Information (PII) Scrubbing

User inputs submitted to conversational assistants are filtered through `sanitize_user_input()`:
- **Social Security Numbers / National IDs**: Masked to `[REDACTED_SSN]`.
- **Payment Card Numbers**: Masked to `[REDACTED_CARD]`.
- **Email Addresses**: Masked to `[REDACTED_EMAIL]`.
- **Telephone Numbers**: Masked to `[REDACTED_PHONE]`.

### Logging Anonymization
All application log sinks pass payloads through `sanitize_for_logging()`. Any dictionary key matching `password`, `secret`, `secret_key`, `token`, `api_key`, or `gemini_api_key` is masked to `[REDACTED_SECRET]`.

---

## 5. Rate Limiting Policy

Rate limiting is enforced via `slowapi` on client IP addresses (or reverse-proxy `X-Forwarded-For`):

| Endpoint Group | Route | Rate Limit | Action on Exceeded |
| :--- | :--- | :--- | :--- |
| **Authentication** | `/api/v1/auth/login` | `10/minute` | HTTP 429 Too Many Requests |
| **Registration** | `/api/v1/auth/register` | `10/minute` | HTTP 429 Too Many Requests |
| **Prediction Inference** | `/predict` | `60/minute` | HTTP 429 Too Many Requests |
| **AI Assistant Chat** | `/api/v1/ai/chat` | `20/minute` | HTTP 429 Too Many Requests |
| **Symptom Screening** | `/api/v1/ai/symptoms` | `15/minute` | HTTP 429 Too Many Requests |
| **Personalized AI** | `/api/v1/ai/personalized` | `10/minute` | HTTP 429 Too Many Requests |
| **Default Endpoints** | All other endpoints | `60/minute` | HTTP 429 Too Many Requests |

---

## 6. Incident Response Plan (IRP)

### Severity Matrix

| Severity Level | Definition | Response SLA | Action Procedure |
| :--- | :--- | :--- | :--- |
| **P1 - Critical** | Model checksum mismatch; credential leak; medical safety bypass. | < 15 minutes | Immediate service shutdown; fail-closed state; notify stakeholders; rotate secrets. |
| **P2 - High** | Gemini API rate limiting or outage; PostgreSQL connection failure. | < 1 hour | Switch to cached/mock fallback; restart DB connection pool; alert administrators. |
| **P3 - Medium** | Degradation in prediction latency (> 100ms); Redis cache disconnection. | < 4 hours | Investigate query plans; check host memory and Redis cluster status. |
| **P4 - Low** | Minor UI visual glitch; non-critical log warning. | < 24 hours | Create standard engineering backlog ticket. |

### Incident Triage Checklist
1. Identify affected endpoint from `/var/log/heartai/error.log`.
2. Inspect health telemetry via `curl http://127.0.0.1:8000/health`.
3. If secrets compromised: execute immediate rotation (Section 2.2).
4. If model corrupted: restore from verified backup and verify SHA-256 (see `BACKUP_AND_RECOVERY.md`).
5. Conduct post-incident retrospective and file incident report.
