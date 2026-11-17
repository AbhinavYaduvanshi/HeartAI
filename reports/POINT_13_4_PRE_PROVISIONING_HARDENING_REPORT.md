# HeartAI — Point 13.4: Pre-Provisioning Safety Hardening Report

**Project**: HeartAI — Cardiovascular Risk Prediction & Health Analytics Platform
**Phase**: Point 13.4 Pre-Provisioning Safety Hardening
**Role**: Senior DevSecOps Engineer & Independent Release Auditor
**Date**: November 17, 2026
**Git Baseline**: `dcc48d632e7bf79a940113e083a8c159aa39ee17` (synchronized with `origin/main`)
**Parent Commit**: `c8cad27c1edb22c942847e58171e7e0025b000ce`
**Execution Scope**: Local verification & implementation only (zero cloud provisioning, zero infrastructure costs, zero Git commits/pushes)

---

## 1. Executive Summary

Following the comprehensive audit in `reports/POINT_13_3_STAGING_READINESS_AUDIT.md`, Point 13.4 was executed to resolve all identified pre-provisioning operational safety issues prior to spinning up a dedicated Ubuntu 24.04 LTS virtual machine.

All targeted remediations have been implemented and locally verified across deployment configurations, provisioning scripts, backup engines, and automated test harnesses:

1. **OP-01 (TLS Certificate Configuration)**: Replaced disparate paths with the canonical certificate pair `/etc/heartai/certs/tls.crt` and `/etc/heartai/certs/tls.key`. Provisioning now validates certificate presence and verifies syntax with `nginx -t` prior to enabling Nginx, failing closed with actionable Tailscale instructions if missing.
2. **OP-03 (VPN-Only Hardening & Anti-Lockout)**: Standardized on `NETWORK_MODE="vpn"` as the safe default. Added pre-flight validation verifying that Tailscale (`tailscale status` / `tailscale0`) or WireGuard (`wg0`) is active and authenticated before modifying UFW firewall rules, preventing accidental administrator SSH lockout.
3. **OP-04 (Provisioning Idempotency & Secret Masking)**: Extracted existing database passwords from `/opt/heartai/.env` on rerun to eliminate credential desynchronization. Completely purged terminal echoes of passwords/secrets. Passed database credentials to PostgreSQL via secure stdin SQL heredoc blocks to prevent process table leakage.
4. **SEC-06 (Encrypted Backup Parity)**: Fixed the OpenSSL fallback pipeline in `deploy/scripts/backup_staging.sh` to stream model tarballs directly through OpenSSL AES-256-CTR into `models.tar.gz.enc`, eliminating unencrypted `models.tar.gz` artifacts on disk. Updated `deploy/scripts/restore_staging.sh` to decrypt encrypted models upon restoration.
5. **Dependency Vulnerability Verification**: Audited environment dependencies with `pip-audit`, confirming zero known CVE vulnerabilities across the active stack.
6. **Verification Gate Expansion**: Enhanced `deploy/scripts/verify_staging.sh` from 14 to 16 comprehensive operational validation checks, incorporating explicit gates for TLS certificate existence/permissions and backup encryption key storage invariants.
7. **Scientific & Application Boundary Preservation**: Full verification that the model SHA-256 (`5dc41520...`), preprocessor SHA-256 (`3a354b5f...`), threshold `0.09`, 25 canonical BRFSS features, emergency symptom isolation, and retrospective research framing are 100% intact.
8. **Test Suite Execution**: Full regression suite passed with **209 passed tests** (0 failures), `ruff check .` reported 0 issues, and `git diff --check` reported 0 whitespace errors.

---

## 2. Git Baseline & Working-Tree State

The repository baseline was validated prior to applying any modifications:

| Check | Expected | Actual Evidence | Status |
| :--- | :--- | :--- | :---: |
| **Current Branch** | `main` | `main` | Verified |
| **HEAD SHA** | `dcc48d632e7bf79a940113e083a8c159aa39ee17` | `dcc48d632e7bf79a940113e083a8c159aa39ee17` | Verified |
| **origin/main SHA** | `dcc48d632e7bf79a940113e083a8c159aa39ee17` | `dcc48d632e7bf79a940113e083a8c159aa39ee17` | Verified |
| **Parent SHA** | `c8cad27c1edb22c942847e58171e7e0025b000ce` | `c8cad27c1edb22c942847e58171e7e0025b000ce` | Verified |
| **Working Tree** | Clean (untracked audit report) | Untracked: `reports/POINT_13_3_STAGING_READINESS_AUDIT.md` | Clean |

---

## 3. Remediation Details & Implementation Analysis

### 3.1 OP-01: Canonical TLS Certificate Architecture
- **Issue**: `deploy/nginx/heartai.conf` pointed to `/etc/letsencrypt/live/your-domain.org/...`, while `DEPLOYMENT_GUIDE.md` referenced `/var/lib/tailscale/certs/...`. Furthermore, `provision_ubuntu24.sh` did not verify certificate presence before attempting to start Nginx, which would cause Nginx service crashes in private Tailscale environments where Let's Encrypt HTTP-01 challenges are inaccessible.
- **Remediation**:
  1. Standardized Nginx configuration on canonical system certificate paths:
     - `ssl_certificate /etc/heartai/certs/tls.crt;`
     - `ssl_certificate_key /etc/heartai/certs/tls.key;`
  2. Updated `deploy/scripts/provision_ubuntu24.sh` to create `/etc/heartai/certs` (`chmod 700`, `chown root:root`).
  3. Added an explicit validation gate in Section 7 of `provision_ubuntu24.sh`:
     - If certificates exist, permissions are enforced (`chmod 644 tls.crt`, `chmod 600 tls.key`) and `nginx -t` verifies syntax before enabling/starting Nginx.
     - If certificates are missing, Nginx is deliberately NOT started, and clear, actionable instructions for `tailscale cert` or manual cert placement are displayed.
  4. Updated `DEPLOYMENT_GUIDE.md` Section 8 to document the canonical paths and exact `tailscale cert` workflow.

### 3.2 OP-03: VPN-Only Ingress & Anti-Lockout Safeguards
- **Issue**: `provision_ubuntu24.sh` defaulted to `NETWORK_MODE="allowlist"` with `127.0.0.1`, which would drop remote SSH connections immediately upon provisioning. In `vpn` mode, UFW rules were previously applied with `|| true` without verifying whether Tailscale was authenticated, creating severe lockout hazards.
- **Remediation**:
  1. Changed default in `deploy/scripts/provision_ubuntu24.sh` to `NETWORK_MODE="${NETWORK_MODE:-vpn}"`.
  2. Added input validation requiring `NETWORK_MODE` to be strictly `vpn` or `allowlist`.
  3. Implemented a pre-flight validation check prior to running `ufw --force reset`:
     - Checks whether `tailscale` is installed and verified via `tailscale status` or interface `tailscale0`.
     - Checks whether WireGuard interface `wg0` is present.
     - If neither VPN interface is active, the script **fails closed immediately with an actionable warning**, aborting before touching UFW rules, completely preventing operator lockout.
  4. Removed silent masking (`|| true`) on UFW rule additions so firewall configuration errors are never ignored.

### 3.3 OP-04: Provisioning Idempotency & Secret Masking
- **Issue**: `provision_ubuntu24.sh` previously generated a new random database password on every invocation without checking `/opt/heartai/.env`, which orphaned existing databases during maintenance runs. Furthermore, line 172 echoed `Generated DB Password: ${DB_PASSWORD}` to the terminal, and credentials were passed as command-line arguments to `psql` (visible in `ps aux`).
- **Remediation**:
  1. Updated Section 4 of `provision_ubuntu24.sh` to inspect `/opt/heartai/.env` for existing `DATABASE_URL` credentials:
     ```bash
     if [ -f "/opt/heartai/.env" ]; then
         EXISTING_DB_PASS=$(grep -E '^DATABASE_URL=' /opt/heartai/.env 2>/dev/null | sed -E 's|^DATABASE_URL=[^:]+://[^:]+:([^@]+)@.*|\1|' || true)
         if [ -n "${EXISTING_DB_PASS}" ]; then
             DB_PASSWORD="${EXISTING_DB_PASS}"
             echo "Reusing existing PostgreSQL password from /opt/heartai/.env."
         fi
     fi
     ```
  2. Switched user creation and password updates to a secure PostgreSQL `DO $$` block executed via `psql` stdin heredoc (`<<EOSQL`), preventing command-line argument credential exposure.
  3. Completely removed `echo "Generated DB Password: ${DB_PASSWORD}"` from script completion output.

### 3.4 SEC-06: Encrypted Backup Model Parity
- **Issue**: In `deploy/scripts/backup_staging.sh`, the OpenSSL fallback path encrypted database streams and `.env`, but archived ML models to disk as unencrypted `models.tar.gz`.
- **Remediation**:
  1. Updated `backup_staging.sh` to stream model tarballs directly through OpenSSL AES-256-CTR with PBKDF2:
     ```bash
     tar -czf - -C /opt/heartai models/ | \
         openssl enc -aes-256-ctr -salt -pbkdf2 \
         -out "${ARCHIVE_PATH}/models.tar.gz.enc" \
         -pass file:"${PASSWORD_FILE}"
     chmod 600 "${ARCHIVE_PATH}/models.tar.gz.enc"
     ```
     Zero unencrypted archive files touch disk storage.
  2. Updated `deploy/scripts/restore_staging.sh` to detect and decrypt `models.tar.gz.enc` before extracting into the temporary restore tree, with fallback support for legacy unencrypted archives.
  3. Reconciled `DEPLOYMENT_GUIDE.md` Section 10 to document OpenSSL streaming encryption parity.

---

## 4. Dependency Vulnerability Verification

A reproducible dependency audit was executed against the active virtual environment using `pip-audit`:

```bash
.venv/Scripts/python -m pip_audit --desc on
```

**Audit Result**:
- **Scanned Packages**: 260+ packages in environment (FastAPI, Uvicorn, NiceGUI, SQLAlchemy, PyJWT, Argon2-cffi, Scikit-learn, XGBoost, PyTorch, Redis, etc.)
- **Advisory Databases Checked**: PyPI Advisory Database & OSV
- **Known Vulnerabilities Found**: **0 (Zero)**
- **Output**: `No known vulnerabilities found`

All production and scientific dependencies satisfy security standards with zero known CVE exposures.

---

## 5. Deployment Verification Gates Enhancement

`deploy/scripts/verify_staging.sh` was upgraded from 14 checks to **16 comprehensive operational checks**:

| Check # | Target Component | Validation Criteria |
| :---: | :--- | :--- |
| **1** | OS & Runtime | Ubuntu 24.04 LTS and Python 3.12 verified |
| **2** | PostgreSQL Service | PostgreSQL 16 active with Alembic version 001 applied |
| **3** | Schema Persistence | Public tables `users` and `prediction_records` exist |
| **4** | Redis Service | Redis 7 active and responding with `PONG` |
| **5** | Rate Limit Storage | Storage URI strictly resolves to `redis://` in staging |
| **6** | Backend Health | `/health` returns `healthy` with `.model.loaded == true` |
| **7** *(New)* | **TLS Certificates** | `/etc/heartai/certs/tls.crt` and `tls.key` exist with `600`/`400` permissions |
| **8** | Nginx Reverse Proxy | Proxies `/health` over HTTPS to FastAPI backend |
| **9** | NiceGUI Frontend | Responds with HTTP 200 on port 8080 |
| **10** | Authentication API | `/api/v1/auth/login` registered in OpenAPI schema |
| **11** | Model Scientific Invariant | `best_model.joblib` SHA-256 matches exact hash |
| **12** | Systemd Supervision | `heartai-backend` and `heartai-frontend` units active |
| **13** | Logging & Audit | `/var/log/heartai` directory exists and accessible |
| **14** | Port Isolation | PostgreSQL (5432) & Redis (6379) bound strictly to loopback |
| **15** *(New)* | **Backup Encryption Key** | `/etc/heartai/backup_key` exists with `400`/`600` permissions |
| **16** | Gemini AI Status | Honestly reports Gemini connectivity status without fabrication |

---

## 6. Scientific Invariants & Clinical Governance Preservation

All scientific, clinical, and safety boundaries were verified post-hardening:

| Invariant | Authoritative Requirement | Current Working Tree | Status |
| :--- | :--- | :--- | :---: |
| **Model Checksum** | `5dc415201016ed1223fd1f4c9cb295e14b2dd64639ad507d63efb16bed51f890` | Verified (`5dc41520...`) | PASS |
| **Preprocessor Checksum** | `3a354b5f6fb66bfce97bfc2ad2d92303e46d98a3e093e7069fefa213afc67055` | Verified (`3a354b5f...`) | PASS |
| **Operating Threshold** | Strictly `0.09` (high-sensitivity CVD screening) | `settings.OPERATING_THRESHOLD == 0.09` | PASS |
| **Feature Schema** | 25 canonical BRFSS survey features | `len(PatientBRFSSInput.model_fields) == 25` | PASS |
| **Symptom Isolation** | Emergency symptoms NEVER in ML feature input | Disjoint set: `symptom_fields ∩ feature_fields == ∅` | PASS |
| **Research Framing** | Retrospective CVD (`_MICHD`) research classification | Research & educational disclaimers intact | PASS |

---

## 7. Test Suite & Code Quality Results

1. **Automated Test Suite**:
   ```
   209 passed in 16.84s (across 18 test modules)
   ```
   Added 6 new unit/regression tests validating OP-01, OP-03, OP-04, and SEC-06 in `tests/test_pre_staging_remediation.py`.

2. **Linter & Code Quality**:
   ```
   .venv/Scripts/python -m ruff check .
   All checks passed!
   ```

3. **Whitespace & Git Check**:
   ```
   git diff --check
   (Clean - 0 whitespace errors, 0 trailing spaces)
   ```

---

## 8. Summary of Modified Files

The following files have uncommitted, verified modifications ready for technical review:

1. `deploy/nginx/heartai.conf`: Updated TLS paths to canonical `/etc/heartai/certs/tls.crt` and `tls.key`.
2. `deploy/scripts/provision_ubuntu24.sh`: Set `NETWORK_MODE="vpn"` default, added Tailscale pre-flight checks, DB password reuse, SQL heredoc, eliminated secret echoes, and added TLS validation gate.
3. `deploy/scripts/backup_staging.sh`: Streamed models to `models.tar.gz.enc` via OpenSSL AES-256-CTR.
4. `deploy/scripts/restore_staging.sh`: Added decryption support for `models.tar.gz.enc`.
5. `deploy/scripts/verify_staging.sh`: Upgraded from 14 to 16 validation checks (TLS and backup key gates).
6. `DEPLOYMENT_GUIDE.md`: Documented canonical TLS paths, Tailscale cert workflow, and OpenSSL model encryption.
7. `tests/test_pre_staging_remediation.py`: Added 6 regression tests covering OP-01, OP-03, OP-04, and SEC-06.

---

## 9. Final Staging Deployment Readiness Verdict

| Audit Domain | Pre-Hardening Status (Point 13.3) | Post-Hardening Status (Point 13.4) |
| :--- | :---: | :---: |
| **TLS Certificate Architecture** | Blocked (OP-01) | **READY** |
| **Firewall & Tailscale Pre-flight** | Blocked (OP-03) | **READY** |
| **Provisioning Idempotency & Secrets** | Blocked (OP-04) | **READY** |
| **Backup Encryption Parity** | Blocked (SEC-06) | **READY** |
| **Dependency Vulnerabilities** | Unverified | **VERIFIED (0 CVEs)** |
| **Deployment Verification Gates** | 14 checks | **16 checks (ENHANCED)** |
| **Scientific & Clinical Boundaries** | Intact | **VERIFIED & PRESERVED** |
| **OVERALL STAGING READINESS** | **BLOCKED** | **AUTHORIZED FOR CONTROLLED STAGING VM PROVISIONING** |
