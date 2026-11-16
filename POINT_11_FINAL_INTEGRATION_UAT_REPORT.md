# HEARTAI — POINT 11 FINAL INTEGRATION & USER ACCEPTANCE TESTING (UAT) REPORT

**Report Title**: Point 11 Final Integration, User Acceptance Testing & System Verification  
**System**: HeartAI Cardiovascular Wellness & Health Awareness Platform  
**Audit Date**: November 16, 2026  
**Auditor**: Senior Integration Architect, DevSecOps Lead & Healthcare Systems Reliability Engineer  
**Audit Status / Verdict**: **ACCEPTED WITH DOCUMENTED LIMITATIONS**  
**Operating Boundary**: **POINT 11 COMPLETE — STOPPED PRIOR TO POINT 12**  
**Clinical Clearance**: **INVESTIGATIONAL RESEARCH USE ONLY (CLINICAL DIAGNOSIS PROHIBITED)**  

---

## 1. Executive Summary & Verification Methodology

Point 11 has been executed as a controlled end-to-end integration-testing and user-acceptance verification phase. The objective was to verify that the existing HeartAI frontend, backend, database layer, calibrated ML inference pipeline, authentication system, Gemini client, and Aarogya Saathi AI companion operate together harmoniously and securely.

To maintain strict scientific and auditing rigor, this review separates verification methods into distinct tiers:

1. **Automated Unit & Component Tests**: 162 automated tests across 15 test files executed via `pytest`, achieving a **100% pass rate** (162 passed, 0 failed, 0 skipped in 22.33s).
2. **API Integration Test Harness**: Programmatic end-to-end testing of REST endpoints via `scripts/run_uat_journeys.py` exercising all 6 user journeys (Journeys A through F) with 100% pass rate.
3. **Genuine Browser-Based UAT**: Live Google Chrome headless automation driven via Chrome DevTools Protocol (CDP) (`scripts/run_browser_uat.py`), capturing 9 genuine screenshots of authentication, assessment submission, Aarogya Saathi emergency triage, dashboard analytics, informed consent toggling, dark theme, and mobile navigation.
4. **Static Analysis & Linting**: `ruff check` on all application code, test suites, and scripts (0 errors, 0 warnings).

The overall verdict is **ACCEPTED WITH DOCUMENTED LIMITATIONS** due to transparently documented operational boundaries:
1. **Live Gemini API Connectivity**: The `GEMINI_API_KEY` in `.env` is configured as a placeholder (`your_gemini_api_key_here`). Per strict safety rules, live upstream generative inference is marked as **NOT VERIFIED**. (Fallback educational messaging, offline safety triage, and local deterministic emergency detection were verified).
2. **Database Engine**: Local testing exercised the SQLite engine (`dialect: sqlite`). PostgreSQL integration is supported architecturally via SQLAlchemy in `app/db/session.py`, but was **UNTESTED LOCALLY** due to the absence of a live local PostgreSQL server.

---

## 2. Windows Pyarrow Investigation & Clean Environment Resolution

### 2.1 Problem Identification & Root Cause
During test execution on Windows 11 Enterprise (64-bit), importing `pandas` failed with:
```text
ImportError: DLL load failed while importing _compute: An Application Control policy has blocked this file.
```
- **Root Cause**: Windows 11 Smart App Control (SAC) / Windows Defender Application Control (WDAC) enforced Code Integrity Policy `{0283ac0f-fff1-49ae-ada1-8a933130cad6}` (Event ID 3077/3118). The C-extension DLL `pyarrow/_compute.cp312-win_amd64.pyd` from the wheel `pyarrow-26.0.1` was unsigned or lacked Authenticode reputation, causing the Windows kernel to reject `LoadLibraryExW`.
- **Failure Mechanism in Pandas**: In `pandas/compat/pyarrow.py`, `import pyarrow as pa` partially succeeded, causing `HAS_PYARROW` to evaluate to `True`. Subsequently, in `pandas/core/arrays/arrow/accessors.py`, unshielded execution of `import pyarrow.compute as pc` triggered the kernel block and raised the fatal `ImportError`.

### 2.2 Review of the Initial Point 11 Workaround
The initial workaround placed a meta-path interceptor `_BlockPyarrowFinder` across `main.py`, `tests/conftest.py`, and `sitecustomize.py`.
A critical technical review determined:
- **Too Broad**: `sitecustomize.py` ran on every Python invocation in `.venv`, altering Python import behavior globally.
- **Application Code Pollution**: Inserting Windows-specific import hooks into `main.py` violated clean architecture, as `pyarrow` is not even a dependency in `requirements.txt`.
- **Dependency Audit**: `pip show pyarrow` confirmed `Required-by: ` was completely empty. HeartAI uses `joblib` and `scikit-learn` for its model pipeline, and `pandas` defaults natively to standard NumPy runtime structures.

### 2.3 Selected Clean Resolution
1. **Uninstalled Extraneous Wheel**: Executed `python -m pip uninstall -y pyarrow`. When `pyarrow` is not installed, `pandas/compat/pyarrow.py` natively catches `ModuleNotFoundError`, sets `HAS_PYARROW = False`, and bypasses all Arrow accessors without errors.
2. **Reverted Application Code**: Reverted `main.py` to its original clean state (`git checkout main.py`). Git diff on `main.py` is now **completely clean (0 changes)**.
3. **Removed Environment Hooks**: Deleted `sitecustomize.py` and `tests/conftest.py`. No monkey-patching of `sys.meta_path` exists anywhere in the repository.
4. **Zero Security Bypass**: Windows Smart App Control remains fully enabled and unmodified.

---

## 3. Git Baseline & Working Tree Status

| Git Metric | Observed Value | Status |
| :--- | :--- | :---: |
| **Branch** | `main` | **PASS** |
| **Baseline Release Commit (Point 9)** | `d175201` | **PASS** |
| **Point 10 UI Implementation Commit** | `817efe5` | **PASS** |
| **Point 10.1 Corrections & Evidence Commit**| `c1d5ae6` | **PASS** |
| **Point 10.1 Documentation Patch Commit** | `876ecae` | **PASS** |
| **Local HEAD Commit** | `876ecae8cff3ec34eda95edd00acaa790b6d0738` | **PASS** |
| **Remote `origin/main` Commit** | `876ecae8cff3ec34eda95edd00acaa790b6d0738` | **PASS** |
| **Remote Divergence** | `0 ahead, 0 behind` (Synchronized) | **PASS** |
| **Modified Tracked Files** | `None` (`main.py` clean) | **PASS** |
| **Untracked Deliverables** | `scripts/run_uat_journeys.py`, `scripts/run_browser_uat.py`, `reports/screenshots/point11_browser/` | **READY** |

---

## 4. Backend & Live Application Telemetry

Live execution of `uvicorn main:app --port 8000` was verified via direct HTTP requests:

### 4.1 Operational Telemetry (`GET /health`)
```json
{
  "status": "healthy",
  "service": "HeartAI Research & Educational Platform",
  "version": "2.1.0",
  "model": {
    "loaded": true,
    "model_id": "heartai-logistic-regression-calibrated-v2",
    "version": "2.1.0",
    "sha256_verified": true,
    "model_sha256_verified": true,
    "operating_threshold": 0.09,
    "preprocessor_sha256_verified": true,
    "feature_count": 25
  },
  "database": {
    "connected": true,
    "dialect": "sqlite"
  }
}
```

### 4.2 Scientific Metadata (`GET /model-info`)
- **Model Architecture**: `CalibratedClassifierCV(LogisticRegression, method='isotonic', cv=5)`
- **SHA-256 Checksum**: `5dc415201016ed1223fd1f4c9cb295e14b2dd64639ad507d63efb16bed51f890`
- **Preprocessor SHA-256**: `3a354b5f6fb66bfce97bfc2ad2d92303e46d98a3e093e7069fefa213afc67055`
- **CDC BRFSS 2023 Cohort**: 318,296 training records / 79,574 test records ($N = 397,870$)
- **Historical Sensitivity (Recall)**: 79.6% at $T = 0.09$
- **Historical Specificity**: 74.3% at $T = 0.09$
- **Target Definition**: Retrospective reported historical cardiovascular disease (`_MICHD: 1=Yes, 0=No`)
- **Disclaimer**: *"Educational research estimate; not a clinical diagnostic device. Evaluates self-reported historical survey patterns, not future incident cardiovascular events."*

### 4.3 Canonical 25-Feature Inference (`POST /predict`)
Submitting a valid 25-feature CDC BRFSS payload returned HTTP 200:
- `estimated_probability`: `0.0132` (1.32%)
- `binary_classification`: `0`
- `operating_threshold`: `0.09`
- `output_type`: `"educational_estimate"`
- `clinical_validation`: `false`
- `consent_recorded`: `false` (when `user_consent_given: false`)

---

## 5. Gemini AI & Aarogya Saathi Safety Integration

| Feature / Verification Step | Scope | Observed Result | Status |
| :--- | :--- | :--- | :---: |
| **Model Configuration** | `app/core/config.py` | Configured to `gemini-3.8-flash` via official `google-genai` SDK | **PASS** |
| **Live Upstream Connectivity** | Gemini API | Placeholder key in `.env`; live API credits not assumed | **NOT VERIFIED** |
| **Degraded Mode / Fallback** | `GET /api/v1/ai/status` | Returns `configured: false` with Google AI Studio setup instructions | **PASS** |
| **Deterministic Emergency Triage** | Regex & symptom patterns | Intercepts acute chest pain, radiation, dyspnea prior to Gemini | **PASS** |
| **Emergency Guidance Hotlines** | Modal banner & responses | Surfaces `112 (National Emergency)` & `102 (Ambulance)` in India, `911` abroad | **PASS** |
| **Symptom Flow Separation** | `POST /api/v1/ai/symptoms` | Dedicated symptom triage route; zero feedback into 25-feature ML input | **PASS** |
| **PII Sanitization** | AI Sanitizer engine | Names, emails, phone numbers, and Aadhaar numbers scrubbed before processing | **PASS** |

---

## 6. Genuine Browser User Acceptance Testing (CDP)

Browser UAT was executed against Google Chrome (Headless CDP) navigating `http://127.0.0.1:8080` (NiceGUI frontend) connected to `http://127.0.0.1:8000` (FastAPI backend).

Nine genuine screenshots were captured and saved into `reports/screenshots/point11_browser/`:

| Journey / Interaction | Repository-Relative Screenshot Path | Viewport | Verification Finding |
| :--- | :--- | :---: | :--- |
| **1. Authentication Modal** | `reports/screenshots/point11_browser/uat_01_browser_auth_dialog.png` | 1440x920 | Sign In modal rendered with email/password inputs and physician login header. |
| **1b. Authentication Success** | `reports/screenshots/point11_browser/uat_01b_browser_auth_success.png` | 1440x920 | Credential submission for `doctor@hospital.org` returned JWT token and welcome notification. |
| **2. Assessment Modal** | `reports/screenshots/point11_browser/uat_02_browser_assessment_modal.png` | 1440x920 | CDC BRFSS 25-feature inputs, BMI, age brackets, and affirmative consent checkbox rendered. |
| **2b. Assessment Result** | `reports/screenshots/point11_browser/uat_02b_browser_assessment_calculated.png` | 1440x920 | "Calculate Risk" submitted payload to `POST /predict`; returned probability and updated risk gauge. |
| **3. Aarogya Saathi Emergency** | `reports/screenshots/point11_browser/uat_03_browser_aarogya_emergency.png` | 1440x920 | Purple glassmorphic modal with online indicator and red 112/102 emergency notice bar rendered. |
| **4. Analytics & Telemetry** | `reports/screenshots/point11_browser/uat_04_browser_analytics_dashboard.png` | 1440x920 | Live SVG ECG monitor, anatomical heart SVG, and 4 vitals gauges rendered in DOM. |
| **5. Consent Interaction** | `reports/screenshots/point11_browser/uat_05_browser_consent_interaction.png` | 1440x920 | Affirmative consent checkbox toggle verified; terms versioning and research disclaimer displayed. |
| **6a. Dark Theme** | `reports/screenshots/point11_browser/uat_06a_browser_dark_theme.png` | 1440x920 | Theme switcher toggled `data-theme="dark"`; cards rendered in dark slate with teal glowing accents. |
| **6b. Mobile Navigation Drawer** | `reports/screenshots/point11_browser/uat_06b_browser_mobile_drawer.png` | 390x844 | Mobile viewport emulation; slide-in navigation drawer with accessible touch links rendered. |

---

## 7. Automated Test Suite Breakdown (162 Tests)

Executed via `.venv\Scripts\python -m pytest`:

| Test Suite File | Tests Collected | Passed | Failed | Skipped | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/test_ai_complete_experience.py` | 23 | 23 | 0 | 0 | **PASS** |
| `tests/test_api.py` | 4 | 4 | 0 | 0 | **PASS** |
| `tests/test_backend_integration.py` | 21 | 21 | 0 | 0 | **PASS** |
| `tests/test_environment.py` | 8 | 8 | 0 | 0 | **PASS** |
| `tests/test_gemini_integration.py` | 20 | 20 | 0 | 0 | **PASS** |
| `tests/test_health_consistency.py` | 7 | 7 | 0 | 0 | **PASS** |
| `tests/test_model_loader.py` | 7 | 7 | 0 | 0 | **PASS** |
| `tests/test_model_metadata.py` | 4 | 4 | 0 | 0 | **PASS** |
| `tests/test_model_registry.py` | 3 | 3 | 0 | 0 | **PASS** |
| `tests/test_motion.py` | 11 | 11 | 0 | 0 | **PASS** |
| `tests/test_prediction.py` | 4 | 4 | 0 | 0 | **PASS** |
| `tests/test_preprocessing.py` | 4 | 4 | 0 | 0 | **PASS** |
| `tests/test_production_readiness.py` | 21 | 21 | 0 | 0 | **PASS** |
| `tests/test_security_hardening.py` | 19 | 19 | 0 | 0 | **PASS** |
| `tests/test_validation.py` | 6 | 6 | 0 | 0 | **PASS** |
| **TOTAL** | **162** | **162** | **0** | **0** | **100% PASS** |

- **Execution Time**: 22.33 seconds
- **Ruff Linter Result**: `All checks passed!` (0 errors, 0 warnings across `app/`, `tests/`, `main.py`, `motion.py`, `motion_demo.py`, `scripts/`).

---

## 8. Defect & Workaround Audit Register

| Defect / Item | Category | Nature of Issue | Resolution Implemented | Impact on Production Code | Status |
| :---: | :---: | :--- | :--- | :--- | :---: |
| **DEF-01** | Compatibility | Windows 11 Smart App Control blocked unsigned `pyarrow._compute.pyd` DLL | Uninstalled extraneous `pyarrow` wheel from `.venv`; removed temporary meta-path finders | `main.py` reverted to 100% clean baseline; zero code pollution | **RESOLVED** |
| **DEF-02** | Static Quality | Unused imports and variables in UAT automation scripts | Cleaned imports and removed unused assignments in `scripts/run_browser_uat.py` | Ruff reports 0 errors across repository | **RESOLVED** |

---

## 9. Remaining Operational Boundaries & Limitations Register

1. **LIM-01: Live Upstream Gemini Connectivity (NOT VERIFIED)**
   - `.env` contains `GEMINI_API_KEY=your_gemini_api_key_here`.
   - HeartAI operates gracefully in educational fallback mode; live multi-turn LLM generation requires the user to insert an active Google AI Studio key.
2. **LIM-02: PostgreSQL Dialect (UNTESTED LOCALLY)**
   - All tests and UAT journeys were validated against SQLite (`dialect: sqlite`).
   - Production deployment with PostgreSQL must validate migrations and concurrent connection pooling against a live PostgreSQL cluster.
3. **LIM-03: Clinical Disclaimer (NON-DIAGNOSTIC)**
   - Model outputs represent retrospective survey correlations on historical data, not individual clinical diagnoses or acute cardiovascular event risk.

---

## 10. Audit Recommendation & Sign-Off

### Recommendation: **READY FOR COMMIT**
All requirements of Point 11 and Point 11.1 have been met:
- Application starts cleanly and passes all health, model-info, and inference tests.
- Extraneous pyarrow workaround has been eliminated; `main.py` has **zero uncommitted changes**.
- 162/162 pytest tests pass with 0 failures and 0 skips.
- Genuine browser UAT executed with 9 screenshots archived in `reports/screenshots/point11_browser/`.
- No clinical claims or production deployment authorizations have been made.
- Execution is stopped prior to Point 12.
