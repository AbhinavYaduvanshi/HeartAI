# HeartAI — Point 13.4A: Final Pre-Provisioning Safety Corrections Report

**Project**: HeartAI — Cardiovascular Risk Prediction & Health Analytics Platform
**Phase**: Point 13.4A Final Pre-Provisioning Safety Corrections Pass
**Role**: Senior DevSecOps Engineer & Release Security Reviewer
**Date**: November 17, 2026
**Git Baseline**: `dcc48d632e7bf79a940113e083a8c159aa39ee17` (synchronized with `origin/main`)
**Parent Commit**: `c8cad27c1edb22c942847e58171e7e0025b000ce`
**Execution Scope**: Local implementation & verification only (no commits/pushes, no cloud provisioning, no costs incurred, no live network/firewall changes)

---

## 1. Executive Summary

Point 13.4A completed a targeted correction and verification pass on the uncommitted Point 13.4 changes following technical-lead review. Five specific operational security and reliability areas were addressed:

1. **Database Credential Reuse & Robust Parsing (OP-04)**: Replaced fragile `grep`/`sed` parsing with standard Python `urllib.parse` facilities in a dedicated helper module (`deploy/scripts/db_credentials_helper.py`). Implemented pre-flight authentication verification on reruns, fail-closed behavior on malformed connection strings, strict single-quote SQL literal escaping, and zero-disclosure error handling.
2. **Backup Cryptography Hardening (SEC-06)**: Standardized on Restic as the **exclusive** backup engine for creating new controlled-staging backups. Eliminated silent fallback to OpenSSL AES-CTR. Added archive path-traversal (Zip Slip) guards (`tar -tzf` inspecting for `..` or absolute paths), required explicit operator authorization for legacy unencrypted archive restoration, and introduced a non-destructive verification drill mode (`--validate-only`).
3. **VPN and Firewall Anti-Lockout Controls (OP-03)**: Verified active Tailscale connectivity (`tailscale status` and local IPv4 allocation) rather than mere interface presence. Replaced disruptive `ufw --force reset` with idempotent, non-destructive rule reconciliation. Implemented dry-run mode (`--dry-run`), interactive operator confirmation, and documented hypervisor-level cloud firewall requirements and out-of-band console recovery.
4. **Deployable Dependency Security Verification**: Clarified the exact scope and methodology of the `pip-audit 2.10.1` vulnerability assessment, distinguishing between installed-environment runtime auditing (225+ packages scanned with 0 CVEs) and requirements-file abstract dependency resolution. Documented reproducible CI audit commands.
5. **Deployment Runbook Reconciliation (`DEPLOYMENT_GUIDE.md`)**: Configured `APP_ENV=staging`, sanitized placeholder URLs to `<OPERATOR_REPOSITORY_URL>` and `<node-name>.<tailnet>.ts.net`, documented the canonical 7-step ordered deployment sequence, labeled database promotion and rollback as state-changing operations, and distinguished non-destructive validation drills from live disaster recovery.

---

## 2. Git Baseline & Working-Tree State

The repository baseline was validated prior to applying any modifications:

| Check | Expected | Actual Evidence | Status |
| :--- | :--- | :--- | :---: |
| **Current Branch** | `main` | `main` | Verified |
| **HEAD SHA** | `dcc48d632e7bf79a940113e083a8c159aa39ee17` | `dcc48d632e7bf79a940113e083a8c159aa39ee17` | Verified |
| **origin/main SHA** | `dcc48d632e7bf79a940113e083a8c159aa39ee17` | `dcc48d632e7bf79a940113e083a8c159aa39ee17` | Verified |
| **Parent SHA** | `c8cad27c1edb22c942847e58171e7e0025b000ce` | `c8cad27c1edb22c942847e58171e7e0025b000ce` | Verified |
| **Working Tree** | Uncommitted Point 13.4 modifications | All Point 13.4 files preserved and refined | Verified |
| **Report Preservation** | 13.3 & 13.4 reports present | `reports/POINT_13_3_STAGING_READINESS_AUDIT.md`, `reports/POINT_13_4_PRE_PROVISIONING_HARDENING_REPORT.md` present | Preserved |

---

## 3. Targeted Technical Corrections

### 3.1 OP-04: Robust Database Credential Reuse & Authentication Validation

#### The Issue
In Point 13.4, credential reuse relied on `grep -E '^DATABASE_URL=' | sed -E 's|^DATABASE_URL=[^:]+://[^:]+:([^@]+)@.*|\1|'`. This custom regular expression failed on passwords containing special characters (`@`, `:`, `/`, `!`, `#`), did not unquote percent-encoded characters (e.g. `%40`, `%2F`), did not verify whether the credential could authenticate against PostgreSQL before reusing it, and passed unescaped strings into SQL heredocs.

#### The Correction
1. Created `deploy/scripts/db_credentials_helper.py` using Python's standard `urllib.parse` (`urlsplit` and `unquote`):
   - Fully parses complex, percent-encoded credentials according to RFC 3986.
   - Validates that the scheme is `postgresql`, and that username, password, and database name are non-empty.
   - Raises sanitized `ValueError` exceptions that omit plaintext credentials from error messages.
   - Provides `escape_pg_string_literal()` which doubles single quotes (`'` -> `''`) for safe PostgreSQL SQL string literals.
2. Updated Section 4 of `deploy/scripts/provision_ubuntu24.sh`:
   - **First-run behavior**: If no `.env` file exists or `DATABASE_URL` is unconfigured, provisions a fresh random password (or uses `HEARTAI_DB_PASSWORD`) and creates role `heartai_user`.
   - **Rerun behavior**: Parses `DATABASE_URL` via the helper. If malformed, **fails closed** (exit 1).
   - **Authentication verification**: If role `heartai_user` already exists, tests authentication via loopback (`PGPASSWORD="${DB_PASSWORD}" psql -h 127.0.0.1 -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1;"`).
     - If authentication succeeds: preserves the active credentials without altering the user's password.
     - If authentication fails: **fails closed immediately** (exit 1) with an error explaining that the role exists but the provided password does not match, preventing accidental lockout.
   - Credentials are never passed on command-line flags (`-W` or `-p`) and are never echoed to stdout, logs, or error streams.

### 3.2 SEC-06: Exclusive Restic Engine & Safe Restoration Guards

#### The Issue
`deploy/scripts/backup_staging.sh` retained an OpenSSL fallback branch that created encrypted archives if Restic was absent. Furthermore, `deploy/scripts/restore_staging.sh` lacked safeguards against malicious archive extraction paths (Zip Slip / path traversal), and did not distinguish non-destructive drills from active database replacements.

#### The Correction
1. **Mandatory Restic Engine**:
   - In `deploy/scripts/backup_staging.sh`, purged the OpenSSL creation fallback entirely.
   - Pre-flight checks verify `restic` binary presence and `/etc/heartai/backup_key` presence (`chmod 400`). If either prerequisite is missing, the script **fails closed immediately** (exit 1).
   - Restic is the sole authorized engine for new backups in controlled staging, enforcing AES-256-CTR + Poly1305 AEAD authenticated encryption.
2. **Path Traversal Protection on Restore**:
   - In `deploy/scripts/restore_staging.sh`, before extracting any tarball (legacy or decrypted), `tar -tzf` inspects archive member paths with `grep -E '(^/|\.\./)'`.
   - If any member contains `..` or starts with `/`, extraction is aborted immediately with `[CRITICAL SECURITY ERROR] Path traversal sequence detected`.
   - All extractions enforce `--no-same-owner`.
3. **Legacy Archive Approval**:
   - Restoring from non-Restic legacy archives requires explicit operator confirmation (`--allow-legacy` or interactive `RESTORE-LEGACY` prompt).
   - Restoring unencrypted legacy files requires `--confirm-unencrypted-legacy`.
4. **Validation Drill vs State-Changing Replacement**:
   - Added `--validate-only` flag to `restore_staging.sh`: extracts to temporary directory, verifies archive header with `pg_restore -l`, restores into isolated scratch database `heartai_db_restore_staging`, verifies tables and Alembic version, and cleans up without touching live services or the active database.
   - Explicitly labeled `--confirm` as **STATE-CHANGING** (stops services, renames active database to rollback snapshot, swaps staging database, and restarts services).

### 3.3 OP-03: VPN Pre-Flight Connectivity & Non-Destructive Firewall

#### The Issue
Checking interface existence (`ip link show tailscale0`) did not guarantee that the node was actually authenticated and connected to the tailnet. Running `ufw --force reset` flushed all existing rules, severing active SSH connections before allow-rules were established.

#### The Correction
1. **Active VPN Connectivity Validation**:
   - Updated `provision_ubuntu24.sh` to require both `tailscale status` success AND non-empty output from `tailscale ip -4`, proving the local node is actively connected to the tailnet.
   - For WireGuard, verifies `wg show wg0`.
   - If neither VPN interface is active and connected, fails closed with an actionable alert before touching firewall rules.
2. **Non-Destructive Rule Reconciliation**:
   - Eliminated `ufw --force reset` in standard provisioning.
   - Rules are added idempotently (`ufw default deny incoming`, `ufw default allow outgoing`, `ufw allow in on <iface> to any port 22`, `ufw allow in on <iface> to any port 443`, followed by `ufw --force enable`).
3. **Dry-Run & Interactive Safety**:
   - Added `--dry-run` (`DRY_RUN=1`) flag: prints planned network checks and planned UFW rules without modifying system state.
   - Added interactive confirmation guard: prompts the operator before modifying firewall rules unless `--confirm-firewall` is supplied.
4. **Cloud Firewall & Out-of-Band Recovery Documentation**:
   - Documented in `DEPLOYMENT_GUIDE.md` Section 10.5 that hypervisor-level Cloud Security Groups must permit UDP port 41641 and that Cloud Serial Console / Virtual Web Terminal / EC2 Instance Connect serves as the out-of-band recovery path if VPN connectivity fails.

### 3.4 Dependency Vulnerability Verification Scope

A comprehensive dependency security scan was conducted using `pip-audit 2.10.1`:

| Parameter | Installed Environment Scan | Requirements File Scan |
| :--- | :--- | :--- |
| **Command** | `.venv/Scripts/python -m pip_audit --local --desc` | `python3 -m pip_audit -r requirements.txt` (CI runner) |
| **Scanner Version** | `pip-audit 2.10.1` | `pip-audit 2.10.1` |
| **Advisory Source** | PyPI Advisory Database & OSV | PyPI Advisory Database & OSV |
| **Packages Audited** | **225+ concrete distributions** in runtime | Abstract version constraints |
| **Known Vulnerabilities** | **0 (Zero CVEs)** | Requires stdlib `venv` for abstract constraint resolution |
| **Exit Code** | `0` | Reproducible in Ubuntu 24.04 CI with `python3-venv` |

**Technical Note on Requirements File Auditing**:
`pip-audit`'s requirements source (`RequirementSource`) creates an ephemeral virtual environment using Python's standard library `venv` module to resolve abstract constraints (e.g. `fastapi>=0.115.0`) into concrete packages. On hosts where Python's `venv` module is absent, scanning the concrete installed environment (`--local`) directly queries the PyPI advisory database for every installed package without virtualization. In the target Ubuntu 24.04 staging VM (where `python3.12-venv` is installed in Step 1 of provisioning), `pip-audit -r requirements.txt` executes natively.

### 3.5 Deployment Guide Reconciliation

Updated `DEPLOYMENT_GUIDE.md` with the following corrections:
1. **Staging Environment Defaults**: Set `APP_ENV=staging` in the primary staging walkthrough; documented production settings separately.
2. **Sanitized Hostnames & URLs**: Replaced dummy domains with `<OPERATOR_REPOSITORY_URL>` and `<node-name>.<tailnet>.ts.net`.
3. **Ordered Deployment Sequence**: Added Section 6.1 documenting the strict operational order:
   `Tailscale Auth -> TLS Certs -> Host Provisioning & UFW -> Nginx Activation -> DB Migrations -> Systemd Startup -> verify_staging.sh`.
4. **Restoration Warnings**: Explicitly documented that `restore_staging.sh latest --confirm` is a **state-changing operation** that replaces the live database. Documented `restore_staging.sh latest --validate-only` for non-destructive drills.
5. **Cloud Firewall & OOB Recovery**: Added Section 10.5 covering UDP 41641, public port isolation, and cloud console recovery.

---

## 4. Test Suite Execution & Verification Evidence

### 4.1 Pytest Regression Suite
Executed the entire test suite across all 18 test modules:
```
============================= test session starts =============================
platform win32 -- Python 3.12.8, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\24abh\OneDrive\Documents\heart health moniter system
configfile: pyproject.toml
plugins: anyio-4.16.0, platformdirs-4.14.5
collected 214 items

214 passed in 16.88s
============================= 214 passed in 16.88s ============================
```

### 4.2 Targeted Pre-Provisioning Tests (`tests/test_pre_staging_remediation.py`)
All 31 targeted regression tests passed (5.84s), including:
- `test_nginx_canonical_tls_paths`: Canonical paths and 0 letsencrypt references.
- `test_provision_script_vpn_mode_default_and_preflight_guard`: VPN default and Tailscale pre-flight checks.
- `test_provision_script_dry_run_and_non_destructive_firewall`: Dry-run mode, confirmation prompt, and no `ufw --force reset`.
- `test_db_credentials_helper_parses_complex_and_percent_encoded_urls`: Robust parsing of `@`, `:`, `/`, `!`, `#`, `%40`.
- `test_db_credentials_helper_rejects_malformed_urls_without_leaking_secrets`: Fail-closed and secret non-disclosure in errors.
- `test_db_credentials_helper_sql_escaping`: Single-quote escaping (`'` -> `''`).
- `test_provision_script_idempotency_and_no_secret_leak`: Integration of helper and zero password prints.
- `test_backup_script_mandates_restic_and_prohibits_fallback`: Restic mandate and zero OpenSSL creation fallback.
- `test_restore_script_tar_traversal_guards`: Active detection of `..` and leading `/` path traversal attempts.
- `test_restore_script_validate_only_mode`: Non-destructive drill validation.
- `test_verify_staging_script_covers_16_checks_including_tls_and_backup_key`: 16 comprehensive checks.

### 4.3 Shell Script Syntax Validation (`sh -n`)
Validated all deployment and operational shell scripts using POSIX `sh -n`:
- `deploy/scripts/provision_ubuntu24.sh`: Clean (exit code 0)
- `deploy/scripts/backup_staging.sh`: Clean (exit code 0)
- `deploy/scripts/restore_staging.sh`: Clean (exit code 0)
- `deploy/scripts/verify_staging.sh`: Clean (exit code 0)

### 4.4 Linter & Whitespace Checks
- `python -m ruff check .`: `All checks passed!` (0 errors)
- `git diff --check`: Clean (0 whitespace errors, 0 trailing spaces, 0 new EOF blank lines)

---

## 5. Scientific & Clinical Boundary Preservation

All core scientific and safety invariants were independently verified:

| Invariant | Authoritative Requirement | Current Working Tree | Status |
| :--- | :--- | :--- | :---: |
| **Model Checksum** | `5dc415201016ed1223fd1f4c9cb295e14b2dd64639ad507d63efb16bed51f890` | Verified (`5dc41520...`) | PASS |
| **Preprocessor Checksum** | `3a354b5f6fb66bfce97bfc2ad2d92303e46d98a3e093e7069fefa213afc67055` | Verified (`3a354b5f...`) | PASS |
| **Operating Threshold** | Strictly `0.09` (high-sensitivity CVD screening) | `settings.OPERATING_THRESHOLD == 0.09` | PASS |
| **Feature Schema** | 25 canonical BRFSS survey features | `len(PatientBRFSSInput.model_fields) == 25` | PASS |
| **Symptom Isolation** | Emergency symptoms NEVER in ML feature input | Disjoint set: `symptom_fields ∩ feature_fields == ∅` | PASS |
| **Clinical Framing** | Retrospective self-reported CVD (`_MICHD`) outcome | Research & educational disclaimers intact | PASS |

---

## 6. Summary of Modified and Added Files

The following files contain verified, uncommitted changes ready for technical review:

| File | Type | Changes Summary |
| :--- | :---: | :--- |
| `deploy/scripts/db_credentials_helper.py` | **New** | Robust RFC 3986 URL parser, SQL literal escaping, safe environment inspection. |
| `deploy/scripts/provision_ubuntu24.sh` | **Modified** | Idempotent DB credential reuse via helper, active Tailscale check, non-destructive UFW reconciliation, dry-run mode, TLS validation gate. |
| `deploy/scripts/backup_staging.sh` | **Modified** | Mandated Restic as sole backup engine, fail closed on missing keys/binaries, removed OpenSSL fallback creation. |
| `deploy/scripts/restore_staging.sh` | **Modified** | Path traversal protection (`tar -tzf`), legacy archive authorization, `--validate-only` drill support. |
| `deploy/scripts/verify_staging.sh` | **Modified** | 16 comprehensive validation gates covering TLS certificates and backup key permissions. |
| `deploy/nginx/heartai.conf` | **Modified** | Standardized on canonical `/etc/heartai/certs/tls.crt` and `tls.key`. |
| `DEPLOYMENT_GUIDE.md` | **Modified** | `APP_ENV=staging`, sanitized URLs, 7-step deployment sequence, state-changing restore warnings, cloud firewall docs. |
| `tests/test_pre_staging_remediation.py` | **Modified** | Added 31 comprehensive regression tests for OP-01, OP-03, OP-04, and SEC-06. |

---

## 7. Remaining Operational Limitations & Live Infrastructure Assumptions

While all code, configurations, and test harnesses are hardened and verified locally, the following operational requirements must be satisfied during live staging VM provisioning:

1. **Host Tailscale Authentication**: The operator must authenticate the node via `sudo tailscale up` before running `provision_ubuntu24.sh` in VPN mode.
2. **MagicDNS TLS Issuance**: Tailscale MagicDNS HTTPS certificates must be issued on the live VM via `tailscale cert` matching the node's actual FQDN.
3. **Cloud VPC Security Group**: The cloud hypervisor must allow outbound HTTPS and inbound UDP port `41641` (Tailscale WireGuard).
4. **Live Integration Drill**: Full end-to-end service startup, live database migration, and live restoration must be validated on the provisioned VM using `verify_staging.sh`.

---

## 8. Final Verdict

$$\mathbf{READY\ FOR\ POINT\ 13.5\ GIT\ INTEGRATION}$$

All five outstanding items from technical-lead review have been resolved, verified with 214 passing tests, checked with zero linter errors, and documented without expanding scope. No commits, pushes, cloud provisioning, or live network changes were performed.
