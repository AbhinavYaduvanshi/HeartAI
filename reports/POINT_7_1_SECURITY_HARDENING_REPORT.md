# HeartAI — Point 7.1: Security Hardening & Final Backend Audit Report

**Audit Date**: November 14, 2026  
**Environment**: Antigravity IDE / Python 3.12.8 / Windows 11  
**Target Commit Baseline**: `d79127a` (Branch: `main`)  
**Production Model Checksum (SHA-256)**: `5dc415201016ed1223fd1f4c9cb295e14b2dd64639ad507d63efb16bed51f890`  
**Preprocessing Pipeline Checksum (SHA-256)**: `3a354b5f6fb66bfce97bfc2ad2d92303e46d98a3e093e7069fefa213afc67055`  
**Test Suite Status**: **88 / 88 Passing (100%)** | **Ruff Lint: 0 Errors** | **OSV Vulnerability Audit: 0 CVEs**  

---

## 1. Executive Summary & Verification of Invariants

In accordance with Point 7.1 requirements, a focused, defense-in-depth security hardening pass was executed across the HeartAI backend and telemetry layers. 

### Invariants Maintained
- **UI & Layout Immutability**: Zero styling, layout, typography, animation, or structural changes to the HeartAI website. All GSAP ScrollTrigger timelines, Tailwind utility classes, and components remain 100% identical.
- **Model & Pipeline Immutability**: The approved Point 6.3 model artifact (`best_model.joblib`) and preprocessing pipeline (`preprocessing_pipeline.joblib`) were not retrained, altered, or re-exported. Both artifacts match their exact cryptographic hashes byte-for-byte.
- **Scientific Terminology & Disclaimer**: All prediction outputs strictly report *"Estimated probability of reported historical cardiovascular disease"*. No future heart attack prediction claims, unsupported clinical risk categories, or diagnostic assertions exist.
- **Halt Condition**: All work is halted at Point 7.1 pending explicit user review and approval.

---

## 2. Security Vulnerabilities Remediated & Hardening Actions

### A. JWT Secret Management & Key Lifecycle
1. **Elimination of Committed Secrets**:
   - Removed all hardcoded `SECRET_KEY` defaults from `app/core/config.py`.
   - Removed committed placeholder strings from `.env.example`.
   - Replaced `.env.example` with instructions on generating high-entropy keys (`python -c "import secrets; print(secrets.token_urlsafe(32))"`).
2. **Fail-Closed Secret Validation**:
   - Implemented strict Pydantic field validation in `Settings`:
     - Fails application startup if `SECRET_KEY` is missing or empty.
     - Enforces a minimum length of 32 characters.
     - Rejects known insecure placeholders (`replace_with_...`, `changeme`, `secret`, `password`, `admin`, etc.).
     - Enforces character diversity/entropy checks ($\ge 8$ unique characters).
3. **Zero-Downtime Secret Rotation**:
   - Introduced `SECRET_KEY_FALLBACK` in configuration.
   - During key rotation, `decode_access_token` verifies signatures against the primary `SECRET_KEY`; if signature validation fails, it attempts verification with `SECRET_KEY_FALLBACK`.
   - Removing `SECRET_KEY_FALLBACK` after a transition period immediately invalidates all legacy sessions.
4. **Zero Secret Logging**:
   - Audited all application loggers: secrets, tokens, passwords, and raw keys are strictly excluded from logs.

### B. Fail-Closed Model & Preprocessing Integrity
1. **Multi-Artifact SHA-256 Verification**:
   - Upgraded `ModelService.load_artifacts()` to verify cryptographic digests for **both** `models/best_model.joblib` and `models/preprocessing_pipeline.joblib`.
   - Updated `models/model_metadata.json` manifest with preprocessing metadata and canonical hash `3a354b5f6fb66bfce97bfc2ad2d92303e46d98a3e093e7069fefa213afc67055`.
2. **Fail-Closed on Missing or Inconsistent Manifests**:
   - Requires non-empty, exactly 64-hex-character expected checksums. If either checksum is blank, omitted, or tampered, `ModelIntegrityError` is raised and startup halts.
   - Enforces valid JSON formatting and required top-level manifest keys (`model_id`, `version`, `sha256_checksum`, `calibration`, `preprocessing`).
3. **Feature Schema & Manifest Verification**:
   - Loads `models/feature_names.json` at startup.
   - Verifies exact feature count equals 25.
   - Validates that feature column ordering matches canonical `ALL_INPUT_FEATURES` identically.
   - Prevents silent feature misalignments or column permutation bugs.

### C. Privacy Hardening: Keyed HMAC-SHA256 vs. Plain Hashing
1. **Re-Identification Risk Analysis of Low-Cardinality Features**:
   - *Vulnerability*: The 25 CDC BRFSS features consist of discrete ordinal tiers (age 1–13, income 1–11, education 1–6) and binary health flags (0 or 1). An unsalted plain SHA-256 digest of normalized feature values is vulnerable to offline dictionary and rainbow-table precomputation attacks. An adversary with access to a leaked table could enumerate common demographic combinations ($\approx 10^7$ plausible combinations) and reverse the hashes to re-identify individuals and their reported health conditions.
2. **Keyed HMAC-SHA256 Mitigation**:
   - Upgraded `hash_patient_input` to `compute_pseudonymous_feature_hmac` using `hmac.new(key, canonical_json, hashlib.sha256)`.
   - Employs a protected server-side pepper secret (`TELEMETRY_HMAC_KEY` or derived via HKDF-like HMAC from `SECRET_KEY`).
   - Because the pepper key is held strictly in environment memory and never persisted in the database, external adversaries cannot perform offline dictionary attacks.
3. **Raw Data Prohibition**:
   - Raw physiological and demographic survey responses are **strictly ephemeral** and never written to persistent disk storage or database tables.
4. **Data Retention & Right to Erasure (GDPR Art. 17 / HIPAA)**:
   - Added `DELETE /api/v1/auth/history` to purge all historical prediction audit records for an authenticated user.
   - Added `DELETE /api/v1/auth/history/{record_id}` to delete a specific record.
   - Anonymous predictions are unlinked to any account.

### D. Explicit Informed Consent Architecture
1. **Privacy by Default**:
   - Consent checkbox in [motion_demo.py](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/motion_demo.py) is unselected by default (`value=False`), complying with GDPR Article 7 requirements for clear affirmative action.
2. **Consent Terms Versioning**:
   - Added `consent_terms_version: str | None` to `PredictionRequest` and `PredictionResponse`.
   - Backend requires `user_consent_given == True` **AND** `consent_terms_version == "2026.1"`.
   - If consent is omitted, false, or terms version is absent/outdated, persistence is completely bypassed.
3. **Transparent Privacy Notice**:
   - Every prediction response includes `privacy_notice` detailing what is stored (keyed HMAC digest, probabilities, threshold flag), why it is stored (calibration auditing), and how to request deletion.

### E. Additional Security Hardening
1. **Algorithm Bounding & JWT Claims**:
   - Hardcoded `algorithms=[settings.ALGORITHM]` ("HS256") in `decode_access_token`.
   - Enforced `options={"verify_signature": True, "verify_exp": True, "require": ["sub", "exp", "iat"]}`. Rejects algorithm substitution ("none") attacks.
2. **Constant-Time Anti-Enumeration Defense**:
   - Mitigated account enumeration timing attacks in `POST /api/v1/auth/login`.
   - When a requested user does not exist, the route calls `verify_dummy_password(password)` against a precomputed Argon2 hash, ensuring response latency is statistically indistinguishable from a valid user lookup with an invalid password.
3. **Rate Limiting on Authentication Endpoints**:
   - Configured `@limiter.limit("10/minute")` on `/api/v1/auth/register` and `/api/v1/auth/login` to prevent credential stuffing and brute-force registration.
4. **Production CORS Guard**:
   - `Settings` validator strictly rejects wildcard `*` origins when `APP_ENV == "production"`.
5. **Dependency Vulnerability Audit**:
   - Scanned all 13 core production dependencies against the Open Source Vulnerabilities (OSV) database via PyPI ecosystem query:
     - `fastapi==0.162.5`: **CLEAN (0 CVEs)**
     - `uvicorn==0.54.0`: **CLEAN (0 CVEs)**
     - `nicegui==4.0.0`: **CLEAN (0 CVEs)**
     - `pydantic==2.14.3`: **CLEAN (0 CVEs)**
     - `pyjwt==2.15.1`: **CLEAN (0 CVEs)**
     - `argon2-cffi==25.1.0`: **CLEAN (0 CVEs)**
     - `slowapi==0.1.10`: **CLEAN (0 CVEs)**
     - `scikit-learn==1.9.1`: **CLEAN (0 CVEs)**
     - `numpy==2.5.4`: **CLEAN (0 CVEs)**
     - `pandas==3.1.1`: **CLEAN (0 CVEs)**
     - `sqlalchemy==2.1.8`: **CLEAN (0 CVEs)**
     - `joblib==1.6.0`: **CLEAN (0 CVEs)**
     - `cryptography==50.0.2`: **CLEAN (0 CVEs)**

---

## 3. Comprehensive Test Results

The automated test suite was expanded from **69 tests to 88 tests** across 11 test modules. All tests pass with zero warnings or failures.

### Execution Summary
```text
============================= test session starts =============================
platform win32 -- Python 3.12.8, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\24abh\OneDrive\Documents\heart health moniter system
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0, platformdirs-4.14.5
collected 88 items

tests\test_api.py ....                                                   [  4%]
tests\test_backend_integration.py .....................                  [ 28%]
tests\test_environment.py ........                                       [ 37%]
tests\test_model_loader.py .......                                       [ 45%]
tests\test_model_metadata.py ....                                        [ 50%]
tests\test_model_registry.py ...                                         [ 53%]
tests\test_motion.py ........                                            [ 62%]
tests\test_prediction.py ....                                            [ 67%]
tests\test_preprocessing.py ....                                         [ 71%]
tests\test_security_hardening.py ...................                     [ 93%]
tests\test_validation.py ......                                          [100%]

============================= 88 passed in 11.62s =============================
```

### Coverage of Point 7.1 Security Hardening Tests
- `test_settings_missing_secret_key_fails`: Startup failure on absent secret key.
- `test_settings_weak_secret_key_fails`: Rejection of secret keys shorter than 32 characters.
- `test_settings_disallowed_placeholder_secret_fails`: Rejection of committed template defaults.
- `test_settings_low_entropy_secret_fails`: Rejection of low-diversity keys.
- `test_jwt_expired_token_rejected`: 401 Unauthorized on expired tokens.
- `test_jwt_invalid_signature_rejected`: 401 Unauthorized on tampered signatures.
- `test_jwt_dual_key_rotation`: Seamless validation via `SECRET_KEY_FALLBACK`.
- `test_model_missing_expected_sha_fails_closed`: Fail-closed on missing model checksum.
- `test_preprocessor_missing_expected_sha_fails_closed`: Fail-closed on missing preprocessor checksum.
- `test_tampered_preprocessing_artifact_fails_closed`: `ModelIntegrityError` on tampered preprocessor.
- `test_feature_manifest_schema_mismatch_fails_closed`: Fail-closed on count/ordering mismatches.
- `test_keyed_hmac_differs_from_plain_sha256`: Keyed HMAC differs from plain hash (prevents rainbow tables).
- `test_consent_omitted_never_persists`: Zero records persisted when consent is omitted.
- `test_consent_false_never_persists`: Zero records persisted when consent is False.
- `test_consent_true_without_terms_version_never_persists`: Zero records persisted without acknowledged terms.
- `test_consent_true_with_valid_terms_persists_keyed_record`: Record persisted with keyed HMAC on valid consent.
- `test_prediction_history_purge_and_single_deletion`: Tests both bulk purge and single-item deletion.
- `test_auth_constant_time_anti_enumeration`: Constant-time response and identical error messages on login failures.
- `test_production_cors_wildcard_rejected`: Rejection of wildcard CORS in production mode.

---

## 4. Modified & Created Files Summary

| File | Change Description |
| :--- | :--- |
| `app/core/config.py` | Removed hardcoded secrets; added strength, placeholder, and production CORS validators; added HMAC pepper key derivation. |
| `app/core/security.py` | Strict algorithm bounding, dual-key rotation fallback, precomputed constant-time dummy password verification. |
| `app/services/model_service.py` | Added preprocessor SHA-256 verification, feature count (25) & ordering manifest checks, fail-closed error handling. |
| `app/services/prediction_service.py` | Implemented keyed HMAC-SHA256 pseudonymization, enforced consent terms version checking, documented privacy risks. |
| `app/schemas/prediction.py` | Added `consent_terms_version`, `privacy_notice` disclosures to request/response schemas. |
| `app/schemas/health.py` | Added `preprocessor_sha256_verified` and `feature_count` to health response. |
| `app/api/routes/auth.py` | Added rate limiting (`10/minute`), constant-time anti-enumeration on login, and `DELETE /history` endpoints. |
| `app/api/routes/health.py` | Updated telemetry response mapping. |
| `models/model_metadata.json` | Registered preprocessing pipeline SHA-256 digest and feature manifest parameters. |
| `motion_demo.py` | Privacy by Default (unselected consent checkbox), clear informed consent disclosure text. |
| `.env.example` | Removed committed secret; added secure generation instructions and rotation documentation. |
| `tests/test_backend_integration.py` | Updated test payloads with `consent_terms_version`. |
| `tests/test_security_hardening.py` | Added 19 comprehensive security-hardening unit and integration tests. |
| `reports/POINT_7_1_SECURITY_HARDENING_REPORT.md` | This comprehensive report. |

---

## 5. Next Steps

In strict adherence to project guidelines:
1. All changes are committed and pushed to `main`.
2. Execution is **HALTED**.
3. Point 8 will not be started without your explicit review and approval.
