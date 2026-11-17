# HeartAI — Point 12.2.1: Provisioning Readiness Technical Audit

**Date**: November 17, 2026  
**Auditor**: Antigravity Autonomous Technical Verification System  
**Baseline Git Commit**: `fbfc50784f146b5951b585f6c779a9cc7687476c` (origin/main synchronized)  
**Target Architecture**: Option A — One Dedicated Ubuntu 24.04 LTS VM (FastAPI, NiceGUI, PostgreSQL 16, Redis 7, Nginx)  
**Audit Purpose**: Git Revision Reconciliation, Network Architecture Disambiguation, Backup & Secrets Security Hardening, Deployment Automation Audit, and Complete Test Suite Verification  
**Final Audit Verdict**: **`READY AFTER SPECIFIC CORRECTIONS`** (Requires Git commit of uncommitted staging foundations and user selection of Network Architecture Alternative A or B prior to cloud provisioning approval)

---

## 1. Git Revision Reconciliation — Critical Analysis

### 1.1 Revision Inspection (`git log`, `git status`, `git ls-files`)
A rigorous inspection was performed on the repository revision history and working tree:
- **Active Git Branch**: `main`
- **Current HEAD Commit**: `fbfc50784f146b5951b585f6c779a9cc7687476c` (`test(uat): complete Point 11 integration and browser acceptance`)
- **Remote Tracking**: `origin/main` at `fbfc50784f146b5951b585f6c779a9cc7687476c` (Fully synchronized)

### 1.2 Status of Point 12.1 Implementation Files
> [!IMPORTANT]
> **CRITICAL REVISION FINDING**:  
> **Commit `fbfc507` does NOT contain the Point 12.1 implementation.**  
> Commit `fbfc507` contains exclusively the Point 11 UAT deliverables (browser screenshots, UAT journey scripts, and health metadata adjustments).  
> All Point 12.1 and Point 12.2 files currently exist **only in the uncommitted local working tree**:
> - `alembic.ini` and `alembic/` (Alembic migration runtime and revision `001_initial_schema.py`) are **untracked**.
> - `deploy/` (`nginx/heartai.conf`, `redis/redis.conf`, `systemd/`, `gunicorn.conf.py`, `scripts/`, `.env.production.template`) is **untracked**.
> - `tests/test_deployment_foundations.py` is **untracked**.
> - `app/core/config.py`, `app/core/rate_limit.py`, `motion_demo.py`, `requirements.txt`, `DEPLOYMENT_GUIDE.md`, and `ENVIRONMENT_CONFIGURATION.md` are **modified but uncommitted**.
> - Reports from prior phases were organized into the `reports/` directory.

### 1.3 Deployment Impact & Recommended Git Revision
- **Impact**: If a remote VM attempted to execute `git clone` from `origin/main` or checkout `fbfc507`, **zero Point 12 deployment assets would exist on the target server**. The VM provisioning script would fail immediately due to missing files.
- **Rule Adherence**: In accordance with user instructions, Antigravity has **not** executed any commit, stash, reset, or push.
- **Recommendation**: Before staging VM provisioning, an authorized Git commit must be executed on `main` (e.g. `feat(deploy): Point 12.1 & 12.2 deployment foundations, staging automation, and provisioning readiness`) so that a distinct, verifiable commit hash exists for the staging VM to clone and run.

---

## 2. Network Architecture Reconciliation

The previous provisioning request contained an operational contradiction: claiming "zero public internet exposure" while simultaneously specifying public-IP-based Nginx reverse proxying and Let's Encrypt ACME HTTP-01 challenges on port 80.

To resolve this ambiguity, two concrete, mutually exclusive network architecture alternatives are defined below:

```mermaid
flowchart TD
    subgraph AltA["Alternative A: VPN / Private Network Staging"]
        ClientA["Evaluator Device (Tailscale / WireGuard)"] -->|Encrypted VPN Tunnel (No Public Ports)| VPNGateway["VPN Interface (tailscale0 / wg0)"]
        VPNGateway --> NginxA["Nginx (Port 443 / SSL)"]
        NginxA --> FastAPIA["FastAPI (127.0.0.1:8000)"]
        NginxA --> NiceGUIA["NiceGUI (127.0.0.1:8080)"]
        style AltA fill:#e8f4fd,stroke:#1b6ec2
    end

    subgraph AltB["Alternative B: IP-Allowlisted Public HTTPS Staging"]
        ClientB["Evaluator Device (Public Static/Whitelisted IP)"] -->|Allowlisted Ingress Only| PublicFW["Cloud Firewall / UFW (Strict IP Whitelist)"]
        PublicFW -->|TCP 22 & 443 (Allowed IPs Only)| NginxB["Nginx (Port 443 / SSL)"]
        PublicFW -.->|All Other IPs| Drop["DROP / FILTERED"]
        NginxB --> FastAPIB["FastAPI (127.0.0.1:8000)"]
        NginxB --> NiceGUIB["NiceGUI (127.0.0.1:8080)"]
        style AltB fill:#fdf4e8,stroke:#c27b1b
    end
```

### Alternative A: VPN / Private-Network-Only Staging (True Zero Public Ingress)
- **Concept**: The staging VM does not expose any listening application ports to the public internet. All staging access occurs over a secure, authenticated overlay mesh (Tailscale or WireGuard) or a cloud VPC private subnet accessible via VPN gateway.
- **Firewall Configuration**:
  - Public Ingress: `DROP` 100% of unsolicited incoming TCP/UDP traffic (stealth host).
  - VPN Interface (`tailscale0` / `wg0`):
    - `TCP 22`: SSH administration allowed only on the VPN IP.
    - `TCP 443`: HTTPS staging web application allowed only on the VPN IP.
    - `TCP 80`: Closed.
  - Loopback (`127.0.0.1`): PostgreSQL (5432), Redis (6379), FastAPI (8000), NiceGUI (8080).
- **TLS Certificate Strategy**:
  - Cannot use Let's Encrypt HTTP-01 challenge (port 80 is not reachable from public Let's Encrypt servers).
  - Strategy 1: ACME DNS-01 Challenge via Certbot DNS plugin (e.g., Cloudflare, Route53) using DNS TXT records without any incoming HTTP traffic.
  - Strategy 2: Internal private CA / `mkcert` with root CA installed on evaluator devices.
- **Evaluation**: Highest security posture; zero attack surface; prevents all internet crawlers and unauthorized traffic. Requires evaluators to join the VPN mesh.

### Alternative B: IP-Allowlisted Public HTTPS Staging (Strict CIDR Gating)
- **Concept**: The VM receives a public static IPv4 address, but cloud security groups (AWS SG, Hetzner Firewall, or DigitalOcean Cloud Firewall) and host UFW drop all traffic from unauthorized IPs.
- **Firewall Configuration**:
  - Ingress:
    - `TCP 22` (SSH): Allowed **only** from explicitly authorized developer IP CIDRs (e.g., `203.0.113.45/32`).
    - `TCP 443` (HTTPS): Allowed **only** from authorized evaluator IP CIDRs.
    - `TCP 80` (HTTP): Allowed **only** from authorized evaluator IP CIDRs (or temporarily opened for Let's Encrypt HTTP-01 validation if DNS-01 is unavailable).
    - Default Policy: `DROP` (packets from non-whitelisted IPs are silently dropped).
  - Loopback (`127.0.0.1`): PostgreSQL (5432), Redis (6379), FastAPI (8000), NiceGUI (8080).
- **TLS Certificate Strategy**:
  - ACME DNS-01 Challenge (preferred, keeps port 80 closed).
  - ACME HTTP-01 Challenge (requires port 80 to be temporarily reachable during certificate issuance).
- **Evaluation**: Direct browser access without VPN client software; simple evaluator access; requires updating firewall rules if evaluator IP is dynamic.

---

## 3. Backup and Recovery Security Audit

A thorough code audit of `deploy/scripts/backup_staging.sh` and `deploy/scripts/restore_staging.sh` identified critical security and operational deficiencies, which have been remediated.

### 3.1 Deficiencies Identified & Remediations Applied
| Component | Initial Deficiency in Script | Applied Hardening & Remediation |
| :--- | :--- | :--- |
| **`.env` Secret Protection** | Copied plaintext `.env` into `${TARGET_DIR}/env_${TIMESTAMP}.bak`. Unencrypted credentials stored on disk. | **Replaced with AES-256-CBC Encryption**: Configuration is encrypted via `openssl enc -aes-256-cbc -salt -pbkdf2` using `/opt/heartai/.backup_key` (`chmod 400`). Plaintext `.env` is never stored in backups. |
| **Dump Integrity Pre-Check** | `restore_staging.sh` dropped the active database before checking if the backup dump file was intact. | **Pre-Restore Validation Added**: Executes `pg_restore -l "${DUMP_FILE}"` to verify archive integrity *before* touching the live database. |
| **Accidental Data Loss** | `restore_staging.sh` dropped `heartai_db` without confirmation or safety flags. | **Safety Confirmation Guard Added**: Requires explicit `--confirm` flag or interactive prompt typing `RESTORE` to execute. |
| **PostgreSQL Restore Auth** | Attempted `pg_restore -U heartai_user -h 127.0.0.1`, which prompts for a password and halts non-interactive automation. | **Peer Authentication Implemented**: Uses `sudo -u postgres pg_restore -d heartai_db --no-owner --role=heartai_user`, bypassing TCP password prompts. |
| **Backup Scheduling Status** | Hourly backup was proposed in documentation but had no executable scheduler. | **Systemd Timer Authored**: Created `deploy/systemd/heartai-backup.service` and `deploy/systemd/heartai-backup.timer` to automate hourly snapshots. |
| **Off-Host Replication** | Backups remained strictly local on the same VM filesystem. | **Replication Hook Implemented**: Added optional `OFFHOST_BACKUP_DEST` supporting encrypted synchronization to AWS S3 (`aws s3 sync --sse AES256`) or Google Cloud Storage. |

### 3.2 Key Management & Retention Policy
- **Encryption Key Storage**: Stored at `/opt/heartai/.backup_key` with strict permissions (`chmod 400`, owned by `root:root`). For production, this key must be escrowed in an off-host secrets vault.
- **Retention**: Local pruning automatically purges snapshots older than 7 days (`find ... -mtime +7 -exec rm -rf {} +`).
- **RPO / RTO Target Status**: Recovery Point Objective (< 1 hour) and Recovery Time Objective (< 30 minutes) remain **unverified engineering targets** until a timed drill is conducted on the live staging host.

---

## 4. Deployment Automation Review

All four deployment scripts in `deploy/scripts/` were reviewed against enterprise standards:

### 4.1 Script Inspection Summary
1. **`provision_ubuntu24.sh`**:
   - **Idempotency**: Checked. Verifies existing users (`id -u heartai`), databases (`pg_database`), and directories before creation.
   - **Privilege Boundaries**: Enforces `DEBIAN_FRONTEND=noninteractive` and creates unprivileged `heartai` service account.
   - **Network Parameterization**: Updated to accept `NETWORK_MODE="vpn"` or `NETWORK_MODE="allowlist"` with `ALLOWED_IPS="<ip1>,<ip2>"`.
   - **Safety**: Generates cryptographically random database passwords via `python3 secrets.token_urlsafe(24)`.
2. **`backup_staging.sh`**:
   - **Encryption**: AES-256-CBC with PBKDF2 encryption on secrets.
   - **Checksums**: Automatically writes `SHA256SUMS.txt` manifest for all artifacts.
   - **Permissions**: Enforces `chmod 700` on directories and `chmod 600` on dump/tarball archives.
3. **`restore_staging.sh`**:
   - **Integrity First**: Validates archive header before database drop.
   - **Service Management**: Stops services before restore, starts services after restore, and queries `/health` to verify operational status.
   - **Safety Guard**: Prevents unconfirmed execution.
4. **`verify_staging.sh`**:
   - **14-Point Automated Test Harness**: Evaluates OS, Python, PostgreSQL, Redis, Gunicorn, Nginx, WebSockets, rate limiting, and model invariants.
   - **No Mock Masking**: Evaluates actual service outputs and port bindings.

---

## 5. Complete Automated Test Suite Results

The complete automated test suite was executed across the entire repository.

### 5.1 Test Execution Metrics
- **Test Command**: `.venv\Scripts\python -m pytest -q`
- **Execution Date**: 2026-11-17 05:41:47 IST
- **Exit Code**: **`0` (SUCCESS)**
- **Total Tests Collected**: **174**
- **Total Tests Passed**: **174 (100%)**
- **Total Tests Failed**: **0**
- **Total Tests Skipped**: **0**

### 5.2 Test Breakdown by Module
| Test Suite File | Test Count | Pass Rate | Status |
| :--- | :---: | :---: | :---: |
| `tests/test_ai_complete_experience.py` | 23 | 100% | **PASSED** |
| `tests/test_api.py` | 4 | 100% | **PASSED** |
| `tests/test_backend_integration.py` | 21 | 100% | **PASSED** |
| `tests/test_deployment_foundations.py` | 12 | 100% | **PASSED** |
| `tests/test_environment.py` | 8 | 100% | **PASSED** |
| `tests/test_gemini_integration.py` | 20 | 100% | **PASSED** |
| `tests/test_health_consistency.py` | 7 | 100% | **PASSED** |
| `tests/test_model_loader.py` | 7 | 100% | **PASSED** |
| `tests/test_model_metadata.py` | 4 | 100% | **PASSED** |
| `tests/test_model_registry.py` | 3 | 100% | **PASSED** |
| `tests/test_motion.py` | 11 | 100% | **PASSED** |
| `tests/test_prediction.py` | 4 | 100% | **PASSED** |
| `tests/test_preprocessing.py` | 4 | 100% | **PASSED** |
| `tests/test_production_readiness.py` | 21 | 100% | **PASSED** |
| `tests/test_security_hardening.py` | 19 | 100% | **PASSED** |
| `tests/test_validation.py` | 6 | 100% | **PASSED** |
| **Total** | **174** | **100%** | **PASSED** |

### 5.3 Code Quality & Linter Results
- **Command**: `.venv\Scripts\python -m ruff check .`
- **Result**: **All checks passed! (0 errors, 0 warnings across all files)**

### 5.4 Alembic Lifecycle Test Execution
- **Command**: `.venv\Scripts\python -m pytest tests/test_deployment_foundations.py -k test_alembic_upgrade_downgrade_lifecycle -v`
- **Exit Code**: `0` (1 passed in 0.57s)
- **Verification**: Complete schema upgrade to `head` (creates `users`, `prediction_records`, `alembic_version`) followed by clean teardown to `base` (drops all tables and indexes with 0 orphaned objects).

### 5.5 Scientific Invariants & Model Checksums
- **Model Checksum (`models/best_model.joblib`)**: `5dc415201016ed1223fd1f4c9cb295e14b2dd64639ad507d63efb16bed51f890` (**EXACT MATCH**)
- **Preprocessor Checksum (`models/preprocessing_pipeline.joblib`)**: `3a354b5f6fb66bfce97bfc2ad2d92303e46d98a3e093e7069fefa213afc67055` (**EXACT MATCH**)
- **Screening Decision Threshold**: `0.09` (**EXACT MATCH**)
- **Input Feature Count**: Exactly 25 canonical CDC BRFSS features (**EXACT MATCH**)
- **Classification Target**: `_MICHD` (1=Yes, 0=No, self-reported historical cardiovascular disease)

---

## 6. Hosting Provider & Region Recommendation

Assuming Option A (single dedicated VM, 2 vCPUs, 4 GB RAM, 40–80 GB NVMe SSD):

| Provider | Plan | Hardware Specs | Monthly Cost | Cost for 48h Staging | Recommendation Justification |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Hetzner Cloud** | **CPX21** | 3 vCPU AMD EPYC, 4 GB RAM, 80 GB NVMe | **~$7.60/mo** | **~$0.53** | **Strongest Recommendation**: Best compute-per-dollar ratio, native hourly billing, fast NVMe, minimal cost for staging. |
| **DigitalOcean** | **Basic Premium** | 2 vCPU AMD, 4 GB RAM, 80 GB NVMe | **$28.00/mo** | **~$2.02** | Excellent alternative: 1-click cloud firewall, zero setup complexity, global data centers. |
| **AWS EC2** | **t3.medium** + gp3 | 2 vCPU, 4 GB RAM, 40 GB gp3 | **~$33.56/mo** | **~$2.21** | Enterprise standard if staging within existing corporate AWS VPC is required. |

- **Recommended Region**:
  - Hetzner: `Ashburn, VA (US)` or `Falkenstein (DE)`
  - DigitalOcean: `NYC3` or `SFO3`
  - AWS: `us-east-1` (N. Virginia)

---

## 7. Remaining Blockers Before Provisioning

Before cloud VM provisioning can commence, the following three specific items must be completed:

1. **Git Commit Authorization**:
   - The Point 12.1 deployment foundations, Alembic migration, systemd units, hardened scripts, and documentation must be staged and committed to `main` so that a reproducible Git commit hash exists for the VM to pull.
2. **Network Architecture Decision**:
   - The user must explicitly select between:
     - **Alternative A**: VPN/Private-Network Staging (Tailscale/WireGuard overlay; zero public ports).
     - **Alternative B**: IP-Allowlisted Public HTTPS Staging (Public IP with strict CIDR firewall restriction).
3. **Explicit Cloud Account / Provisioning Approval**:
   - The user must authorize the specific cloud provider (Hetzner, DigitalOcean, or AWS) and provide SSH public key details.

---

## 8. Final Audit Verdict

### Verdict:
# **`READY AFTER SPECIFIC CORRECTIONS`**

### Summary of Condition:
The technical foundations, automation scripts, test suites (174/174 passed), and security mitigations are complete and verified.  
Once the user authorizes the Git commit of Point 12.1/12.2 assets and selects Network Architecture Alternative A or B, the repository will transition immediately to **`READY FOR PROVISIONING APPROVAL`**.

### Strict Stopping Boundary Confirmation:
- Zero VMs created.
- Zero cloud accounts charged or modified.
- Zero DNS records or TLS certificates issued.
- Zero Git commits or pushes executed.
- Execution halts here pending user instructions.
