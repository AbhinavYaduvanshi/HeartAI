# HEARTAI — POINT 9 BASELINE INSPECTION REPORT

**Date**: November 14, 2026  
**Lead Auditor / Architect**: Senior Software Architect, DevSecOps Engineer, QA Automation Lead & Reliability Engineer  
**Active Branch**: `main`  
**Latest Baseline Commit**: `2c83da9` (`docs(audit): Point 8.1 final acceptance audit and report verification`)  
**Point 8.1 Implementation Commit**: `a5e7239`  
**Working Tree State**: Clean (Verified via `git status`)  
**Baseline Test Suite Status**: 138 / 138 Passing (100%)  
**Model Artifact SHA-256 Checksums**:
- `best_model.joblib`: `5dc415201016ed1223fd1f4c9cb295e14b2dd64639ad507d63efb16bed51f890`
- `preprocessing_pipeline.joblib`: `3a354b5f6fb66bfce97bfc2ad2d92303e46d98a3e093e7069fefa213afc67055`
- Operating Threshold: `0.09` (Screening Sensitivity: ~79.60% CV / 79.82% Test)

---

## 1. Repository Structure & Configuration Inspection

### 1.1 Structural Inventory
- **Application Core (`app/`)**:
  - `app/ai/`: Generative AI layer with Aarogya Saathi assistant (`assistant.py`), prompts (`prompts.py`), safety filters (`safety.py`), and Google GenAI client (`gemini_client.py`).
  - `app/api/`: REST routing layer (`deps.py`) with mounted routers: `health.py`, `auth.py`, `predict.py`, `model_info.py`, `ai.py`.
  - `app/core/`: Application settings via pydantic-settings (`config.py`), rate limiting (`rate_limit.py`), cryptographic utilities with Argon2id and HS256 JWT (`security.py`).
  - `app/db/`: SQLAlchemy 2.0 ORM models (`models.py`) and engine/session manager with SQLite/PostgreSQL support (`session.py`).
  - `app/ml/`: Model loader, metadata schemas, inference pipeline, preprocessing pipeline, and legacy registry.
  - `app/schemas/`: Pydantic V2 schemas for AI, prediction, health, user authentication, and consent.
  - `app/services/`: Model service with SHA-256 verification, and trusted consent service.
- **Frontend & Motion Engine**:
  - `main.py`: FastAPI clinical API server with static mounts.
  - `motion_demo.py`: NiceGUI application page featuring interactive assessment, symptom triage, Aarogya Saathi chat, vital gauges, and SVG animations.
  - `motion.py` & `static/`: GSAP 3, ScrollTrigger, Lottie, and `heartai-motion.css` supporting `prefers-reduced-motion`.
- **Test Infrastructure (`tests/`)**:
  - 138 tests across 6 active test modules covering authentication, prediction, model loader, health status consistency, security hardening, and generative AI experience.
- **Models & Artifacts (`models/`)**:
  - `best_model.joblib`, `preprocessing_pipeline.joblib`, `model_metadata.json`, `evaluation_report_final.json`.

---

## 2. Review of Point 8.1 Findings & Operational Risks

From `reports/POINT_8_1_FINAL_ACCEPTANCE_AUDIT.md`, the following architectural boundaries and operational areas were documented:

1. **In-Memory Rate Limiting Limitation**:
   - `slowapi` currently defaults to in-memory tracking. In horizontal multi-worker or containerized deployments (e.g. Uvicorn/Gunicorn with multiple worker processes), rate limits are not shared across workers without an optional distributed store (e.g., Redis).
2. **Emergency Pre-Screening Boundaries**:
   - Deterministic keyword regex executes in `< 0.1 ms`. However, severely misspelled terms (e.g. *"crushng chest pain"*) or metaphorical descriptions bypass regex into secondary triage. Safe, deterministic keyword expansions can be explored without introducing false positives.
3. **Database Connection Pooling & Migration Readiness**:
   - SQLite user-directory database is used for development. For staging/production preparation, robust PostgreSQL pooling parameters (`pool_size`, `max_overflow`, `pool_recycle`), database error recovery, and migration strategies must be documented and verified.
4. **Unverified Live Gemini API Key**:
   - `GEMINI_API_KEY` is currently unconfigured in the local environment, meaning live API requests remain unverified while mocked/error paths pass 100%.

---

## 3. Scope & Objectives for Point 9

Point 9 will address:
1. **End-to-End User Journey Verification**: Rigorously test all contracts between frontend schemas and backend routes.
2. **Deterministic Emergency Screening Strengthening**: Add safe, tested common spelling and phrasing variants (e.g., "suffocation", "heaviness on chest", "crushing pain", "radiating to shoulder") while preserving zero false reassurance.
3. **Multi-Worker Rate Limiting Architecture**: Provide dual-mode rate limiter supporting in-memory for local dev and Redis-backed storage when `REDIS_URL` is configured.
4. **Database & Production Readiness**: Verify PostgreSQL connection pooling configurations, backup/restoration procedures, and health check diagnostics.
5. **Security & Dependency Audit**: Run pip/safety/pip-audit or dependency verification and ensure zero secrets are exposed.
6. **Production Documentation**: Produce all 6 required documentation files (`PRODUCTION_READINESS_REPORT.md`, `DEPLOYMENT_GUIDE.md`, `SECURITY_OPERATIONS.md`, `ENVIRONMENT_CONFIGURATION.md`, `BACKUP_AND_RECOVERY.md`, `KNOWN_LIMITATIONS.md`).
7. **Complete Automated Testing**: Run full regression test suite, ensure 0 lint errors, verify model checksums, and prepare final acceptance report.

**Boundary Commitment**: No public deployment, no model changes, no UI redesign.
