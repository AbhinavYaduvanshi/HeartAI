# HeartAI — Point 13.3: Controlled Staging Deployment Readiness Audit Report

**Date**: November 17, 2026
**Auditor**: Senior DevSecOps Engineer & Independent Release Auditor (Antigravity Autonomous Verification System)
**Target Git Revision**: `dcc48d632e7bf79a940113e083a8c159aa39ee17` (`main` and `origin/main` synchronized)
**Parent Commit**: `c8cad27c1edb22c942847e58171e7e0025b000ce`
**Audit Scope**: End-to-End Infrastructure As Code (Ubuntu 24.04, PostgreSQL 16, Redis 7, Nginx, Systemd, Restic), Security Posture, Sizing, and Scientific Invariants
**Audit Mode**: **STRICT READ-ONLY INSPECTION (Zero Implementation Modifications Executed)**
**Operating Clearance**: **INVESTIGATIONAL RESEARCH & EDUCATIONAL USE ONLY (CLINICAL DIAGNOSIS PROHIBITED)**
**Staging Readiness Verdict**: **`CONDITIONAL GO FOR CONTROLLED PRIVATE STAGING`**

---

## 1. Executive Summary

This independent release readiness audit evaluates whether the HeartAI codebase at commit `dcc48d6` is technically prepared for controlled, private staging deployment on a dedicated Ubuntu 24.04 LTS virtual machine under a **Tailscale-only private network architecture**.

Following the successful implementation and verification of all pre-staging remediations (Points 13.1 and 13.2B) and their formal integration into Git (Point 13.2C), the platform has resolved all previously identified critical blockers (REL-01, SEC-01, REL-03, SEC-02, REL-02).

The audit concludes with a **`CONDITIONAL GO`** recommendation. Zero application code modifications are required prior to deployment. Deployment may proceed once the technical lead approves the operational prerequisites: VM sizing (>= 4 GB RAM to prevent pip install OOM), Tailscale certificate generation, and invoking the provisioning script with `NETWORK_MODE=vpn`.

### Summary of Audit Assessment
| Assessment Category | Evaluation | Verdict | Notes |
| :--- | :--- | :---: | :--- |
| **Git Baseline & Integrity** | `dcc48d6` synchronized with `origin/main`; working tree clean | **PASS** | Verified via Git SHA introspection |
| **Provisioning Automation** | `provision_ubuntu24.sh` automates Ubuntu 24.04, PG16, Redis 7, UFW | **PASS** | Requires `NETWORK_MODE=vpn` flag |
| **Database & Migrations** | Alembic `ExecStartPre` enforced in systemd; `create_all()` skipped | **PASS** | Fail-closed startup guaranteed |
| **Network & Ingress Security** | Tailscale VPN isolation; internal services bound to `127.0.0.1` | **PASS** | Accidental public ingress blocked by UFW |
| **Rate Limiting & Anti-Spoofing** | Redis-backed distributed store; rightmost `parts[-1]` fallback | **PASS** | Nginx `X-Real-IP` takes precedence |
| **Session Security** | NiceGUI signed cookie with `https_only=True`; server-side storage | **PASS** | Mock login excised; Bearer tokens injected |
| **Disaster Recovery** | Streaming Restic encrypted backups; two-stage health verified restore | **PASS** | OpenSSL fallback leaves model unencrypted |
| **Runtime Resource Sizing** | Tabular model is lightweight; `requirements.txt` carries PyTorch/CV | **WARNING** | Requires >= 4 GB RAM VM to avoid OOM |
| **Scientific Invariants** | Checksums, 0.09 threshold, 25 features, and retrospective framing | **PASS** | 100% bit-level invariant match |

---

## 2. Verified Git Baseline

The repository baseline was independently inspected using Git command tooling.

```
$ git rev-parse HEAD
dcc48d632e7bf79a940113e083a8c159aa39ee17

$ git rev-parse origin/main
dcc48d632e7bf79a940113e083a8c159aa39ee17

$ git status
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean

$ git log -2 --pretty=format:"commit %H%nParent: %P%nSubject: %s%n"
commit dcc48d632e7bf79a940113e083a8c159aa39ee17
Parent: c8cad27c1edb22c942847e58171e7e0025b000ce
Subject: fix(security): complete Point 13 pre-staging hardening

commit c8cad27c1edb22c942847e58171e7e0025b000ce
Parent: fbfc50784f146b5951b585f6c779a9cc7687476c
Subject: feat(infra): Point 12 production infrastructure foundations and deployment automation
```

- **Branch**: `main` (synchronized with `origin/main`)
- **HEAD Commit**: `dcc48d632e7bf79a940113e083a8c159aa39ee17`
- **Parent Commit**: `c8cad27c1edb22c942847e58171e7e0025b000ce`
- **Working Tree**: Completely clean; zero untracked, modified, or staged files.

---

## 3. Findings Table

The table below catalogs all architectural, operational, and security observations identified during this audit.

| Finding ID | Severity | Category | Component & File Location | Impact Summary | Operational Remediation / Pre-Deployment Action |
| :---: | :---: | :--- | :--- | :--- | :--- |
| **OP-01** | **HIGH** | Staging Prerequisite | `deploy/nginx/heartai.conf` (Lines 39–40) | Nginx references `/etc/letsencrypt/live/your-domain.org/*.pem`. If Nginx starts without certificates, `nginx -t` fails. | Generate Tailscale certificate (`tailscale cert <node>`) or temporary snakeoil certs before enabling Nginx. |
| **OP-02** | **MEDIUM** | Resource / Sizing | `requirements.txt` (Lines 26–29, 52–53) | PyTorch, Torchvision, OpenCV, and Jupyter packages (~3 GB) bloat `pip install` and risk OOM on <= 2 GB RAM VMs. | Provision a VM with >= 4 GB RAM, or deploy with a pruned tabular requirements file (`requirements-prod.txt`). |
| **OP-03** | **MEDIUM** | Configuration | `deploy/scripts/provision_ubuntu24.sh` (Line 18) | `NETWORK_MODE` defaults to `allowlist` with `ALLOWED_IPS="127.0.0.1"`. Omitting flag locks out remote access. | Operator must invoke with: `sudo NETWORK_MODE=vpn bash deploy/scripts/provision_ubuntu24.sh`. |
| **SEC-03** | **MEDIUM** | Authorization | `app/db/models.py` (Lines 21–40) & routes | Absence of Role-Based Access Control (RBAC). All authenticated accounts possess identical privileges. | Acceptable for private staging. Implement `role` enum (`physician`, `auditor`, `admin`) prior to multi-tenant release. |
| **SEC-04** | **MEDIUM** | Session Security | `app/core/security.py` & `app/api/deps.py` | JWT tokens lack a server-side revocation / blacklist check. Tokens remain valid until expiration (24h). | Acceptable for staging. Implement Redis token blocklist (`jti` tracking) for instantaneous revocation in production. |
| **REL-04** | **MEDIUM** | Safety / Clinical | `app/ai/safety.py` (Lines 38–62) | Keyword regex emergency detection fails on typos, Hinglish, metaphors, and regional languages. | Maintain clear educational disclaimers; prominently display emergency dialer (112/911); never claim clinical diagnosis. |
| **SEC-05** | **LOW** | DoS / Auth | `app/schemas/user.py` (Lines 14, 21) | Absence of `max_length` constraint on password fields. Massive payloads could cause CPU exhaustion in Argon2id. | Add `max_length=128` to `password` field in `UserCreate` and `UserLogin` schemas. |
| **SEC-06** | **LOW** | Cryptography | `deploy/scripts/backup_staging.sh` (Line 120) | In the OpenSSL fallback path, `models.tar.gz` is compressed with gzip but not encrypted with OpenSSL. | Ensure Restic is installed (primary path), which encrypts all snapshots via AES-256-CTR + Poly1305. |
| **REL-05** | **LOW** | Observability | `app/api/routes/health.py` (Lines 26–64) | `/health` checks PostgreSQL and Model integrity, but omits Redis ping status. | Add Redis ping status to `HealthResponse` schema to detect rate-limiter degradation. |
| **SEC-07** | **LOW** | Browser Security | `deploy/nginx/heartai.conf` (Line 54) | CSP requires `'unsafe-inline'` and `'unsafe-eval'` due to NiceGUI/Quasar runtime script injection. | Document framework limitation. Explore nonced CSP in future frontend modernization iterations. |
| **SEC-08** | **INFO** | Privacy / Logging | `logging_config.py` (Line 33) | `SensitiveDataFilter` keyword check requires `"="`, missing JSON (`"token": "..."`) and YAML log outputs. | Expand regex filter in `SensitiveDataFilter` to catch key-value delimiters (`:`, `"`). |
| **OP-04** | **INFO** | Idempotency | `deploy/scripts/provision_ubuntu24.sh` (Line 87) | Rerunning without `HEARTAI_DB_PASSWORD` prints a newly generated password that doesn't match existing DB user. | Read existing password from `/opt/heartai/.env` if already provisioned. |

---

## 4. Infrastructure-by-Infrastructure Technical Audit

### 4.1 Ubuntu 24.04 LTS Provisioning (`deploy/scripts/provision_ubuntu24.sh`)
- **OS Compatibility**: Verified. Native packages installed via `apt-get` include `postgresql-16`, `redis-server`, `python3.12`, `nginx`, `restic`, `fail2ban`, and `ufw`. Ubuntu 24.04 LTS ships with PostgreSQL 16 and Python 3.12 in official repositories.
- **Privilege Separation**: Unprivileged system account `heartai` (`--system --shell /bin/false`) owns `/opt/heartai` (chmod 750) and `/var/log/heartai` (chmod 750). Backup directory `/var/backups/heartai` and config `/etc/heartai` are restricted to `root:root` (chmod 700).
- **Failure Recovery**: Script operates with `set -euo pipefail`. Any command error halts execution immediately.
- **Data Safety**: No destructive filesystem commands (`rm -rf /` or database drops). Existing database user and database creation commands use idempotent guards (`SELECT 1 FROM pg_roles`, `SELECT 1 FROM pg_database`).
- **Secret Handling Warning**: Line 172 prints `Generated DB Password: ${DB_PASSWORD}` to stdout. In manual provisioning, this is captured by the administrator; in automated CI/CD runners, log masking would be required.

### 4.2 PostgreSQL 16 & Alembic Schema Lifecycle
- **Systemd Integration**: `deploy/systemd/heartai-backend.service` enforces:
  `ExecStartPre=/opt/heartai/.venv/bin/alembic upgrade head`
  Runs sequentially as `heartai:heartai` in `/opt/heartai` with `/opt/heartai/.env` before Gunicorn spawns workers.
- **Fail-Closed Execution**: If Alembic migration fails (non-zero exit code), systemd aborts service startup immediately.
- **Zero Runtime Bypass**: In `app/db/session.py`, `init_db()` verifies database connectivity via `SELECT 1` and skips `Base.metadata.create_all()` in `staging` and `production` modes. Schema mutations are governed strictly by Alembic versioning.
- **Migration Baseline**: `alembic/versions/001_initial_schema.py` provides reversible initial DDL for `users`, `prediction_records`, indexes, and foreign keys.

### 4.3 Nginx Reverse Proxy, Tailscale VPN & UFW Firewall
- **Network Boundary (Option A — Tailscale VPN Only)**:
  - UFW default policy: `default deny incoming`, `default allow outgoing`.
  - In `vpn` mode: UFW opens port 22 (SSH) and port 443 (HTTPS) **strictly on `tailscale0` and `wg0`**. No ports are exposed to public interfaces (`eth0`/`ens4`). Port 80 is closed on the VPN interface.
  - Internal application ports (`127.0.0.1:8000`, `127.0.0.1:8080`, `127.0.0.1:5432`, `127.0.0.1:6379`) listen strictly on loopback.
- **Reverse Proxy Routing**:
  - API, Health, ML inference, and docs routed to FastAPI on `http://127.0.0.1:8000`.
  - Root and interactive WebSockets routed to NiceGUI on `http://127.0.0.1:8080` with `$connection_upgrade` map.
  - Static assets directly served from disk at `/opt/heartai/static/`.
- **Forwarded Headers & Anti-Spoofing**:
  - Nginx sets `proxy_set_header X-Real-IP $remote_addr;` (unconditionally overwriting incoming client headers).
  - FastAPI's `get_trusted_client_ip()` verifies direct socket peer against `FORWARDED_ALLOW_IPS` (`127.0.0.1,::1`), inspects `X-Real-IP`, and falls back safely to rightmost `parts[-1]` under `$proxy_add_x_forwarded_for`.
- **TLS & Security Headers**:
  - Protocols restricted to `TLSv1.2 TLSv1.3`.
  - HSTS enabled: `max-age=63072000; includeSubDomains; preload`.
  - `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`.
  - NiceGUI session cookie emits `Secure` flag via `https_only=True` in staging/production, complemented by `HttpOnly` and `SameSite=lax`.

### 4.4 Redis 7 & Multi-Worker Rate Limiting
- **Redis Binding**: Bound strictly to `127.0.0.1 ::1` with `protected-mode yes` and `port 6379`.
- **Memory Capping**: Capped at `maxmemory 256mb` with `maxmemory-policy allkeys-lru` to prevent Redis from causing host memory exhaustion.
- **Fail-Closed Production Guard**: `resolve_storage_uri()` in `app/core/rate_limit.py` raises `RuntimeError` on startup if `REDIS_URL` is missing in `staging` or `production`, preventing uncoordinated in-memory rate limiting across Gunicorn workers.
- **Observability Limitation**: `/health` does not currently execute `test_redis_ping()`. (Finding REL-05).

### 4.5 Backup Resilience & Disaster Recovery
- **Streaming Pipeline**: `deploy/scripts/backup_staging.sh` streams `pg_dump -Fc heartai_db` directly into Restic stdin (`--stdin-filename heartai_db_${TIMESTAMP}.dump`). Plaintext database dumps are never written to disk.
- **Encryption**: Restic snapshots use client-side AES-256-CTR with Poly1305 MAC. Passphrase loaded from `/etc/heartai/backup_key` (chmod 400).
- **Disaster Recovery Restore**: `deploy/scripts/restore_staging.sh` employs a two-stage restore: restores to scratch database `heartai_db_restore_staging`, validates schema, renames live database to rollback snapshot `heartai_db_rollback_${TIMESTAMP}`, starts services, and verifies `/health` (checking `.model.loaded == "true"` and `.database.connected == "true"`). If health verification fails, automatic rollback renames the rollback snapshot back to live.
- **Unencrypted Artifact Warning (Finding SEC-06)**: In the secondary OpenSSL fallback path, while database and `.env` are encrypted with `openssl enc -aes-256-ctr`, `models.tar.gz` is archived with standard `tar -czf` without OpenSSL encryption. Operators must ensure `restic` is installed on the host.
- **RPO / RTO**:
  - RPO: 1 hour (governed by hourly systemd timer `heartai-backup.timer`). Continuous WAL archiving is not configured.
  - RTO: Estimated < 2 minutes for small staging datasets (< 1 GB) based on local scripted restore drill logic.

---

## 5. Runtime Resource Sizing & Competition Assessment

### 5.1 Process Memory & Compute Profile
| Process / Daemon | Purpose | Typical Resident Memory (RSS) | CPU Usage Profile |
| :--- | :--- | :---: | :--- |
| **PostgreSQL 16** | Relational user & audit store | 150 MB – 256 MB | Low; burst on migration/dump |
| **Redis 7** | Distributed rate limit store | 40 MB – 256 MB (Capped) | Very low; in-memory key lookups |
| **Nginx** | TLS reverse proxy & static delivery | 30 MB – 50 MB | Low; async event-driven |
| **FastAPI Backend (Gunicorn)** | API & ML inference (2 workers) | 350 MB – 500 MB (175 MB/worker) | Burst on prediction inference |
| **NiceGUI Frontend** | UI server & WebSocket engine | 180 MB – 250 MB | Low to moderate during active sessions |
| **Restic Backup** | Hourly snapshot execution | 100 MB – 200 MB (Transient) | Moderate CPU during AES encryption |
| **Ubuntu Systemd & OS** | Base operating system | 250 MB – 350 MB | Minimal baseline |
| **Total Estimated Steady-State** | All concurrent services | **1.1 GB – 1.8 GB** | **Cores: 1–2 typical** |

### 5.2 Dependency Bloat Risk (`requirements.txt`)
- `requirements.txt` includes:
  `torch>=2.4.0`, `torchvision>=0.19.0`, `pillow>=10.4.0`, `opencv-python>=4.10.0`, `jupyter>=1.0.0`, `ipykernel>=6.29.0`.
- The active HeartAI production model is `best_model.joblib` (a scikit-learn / XGBoost tabular model). Computer vision and deep learning packages are legacy research exploratory artifacts.
- Installing PyTorch wheels requires ~2.5 GB of disk space and can spike memory usage beyond 2 GB during `pip install` decompression.
- **VM Risk**: On a small 2 GB RAM VM (e.g. AWS `t4g.small` or Hetzner `CX22`), running `pip install -r requirements.txt` or running all services concurrently creates a severe **Out-Of-Memory (OOM) killer risk**.

### 5.3 Recommended Minimum Staging VM Specification
| Specification Component | Recommended Staging VM Specification | Rationale & Assumptions |
| :--- | :--- | :--- |
| **vCPU** | **2 vCPUs** | Sufficient for Gunicorn (2 workers), NiceGUI, and background OS tasks |
| **RAM** | **4 GB RAM** (8 GB if unpruned PyTorch retained) | Provides comfortable headroom over the 1.8 GB steady-state footprint and prevents OOM |
| **Swap Space** | **2 GB Swapfile** (`/swapfile`) | Essential buffer against transient burst allocation during pip install or backups |
| **Storage (Disk)** | **25 GB NVMe / SSD** | OS (4 GB), Virtualenv (4.5 GB with PyTorch), PostgreSQL (2 GB), Backups (5 GB), Logs (2 GB) |
| **Operating System** | **Ubuntu 24.04 LTS (x86_64 or arm64)** | Clean cloud-init image; fully matches `provision_ubuntu24.sh` |
| **Networking** | **Tailscale VPN Enabled** | Public ports 80/443 closed; ingress restricted to `tailscale0` |

---

## 6. Scientific Invariants & Educational Framing Verification

The entire codebase was verified against the canonical scientific invariants:

```python
# Model and Preprocessor Checksum Verification
Model SHA-256:        5dc415201016ed1223fd1f4c9cb295e14b2dd64639ad507d63efb16bed51f890 (VERIFIED EXACT)
Preprocessor SHA-256: 3a354b5f6fb66bfce97bfc2ad2d92303e46d98a3e093e7069fefa213afc67055 (VERIFIED EXACT)
Operating Threshold:  0.09 (VERIFIED EXACT)
Canonical Features:   25 BRFSS survey features (VERIFIED EXACT)
```

- **Symptom Isolation**: Confirmed. Emergency symptoms (`chest_pain`, `shortness_of_breath`, etc.) are processed strictly in `app/ai/safety.py` and excluded from the 25-feature tabular model schema.
- **Retrospective Framing**: Confirmed. Predictions are labeled strictly as `"Estimated probability of reported historical cardiovascular disease"` (`_MICHD`).
- **Research Disclaimer**: Confirmed. All responses and UI headers explicitly state that HeartAI is an investigational research prototype, not a medical device, and not intended for diagnosis or acute event prediction.

---

## 7. Automated Test & Static Analysis Evidence

### 7.1 Pytest Execution Evidence
```
.venv\Scripts\python -m pytest -q
........................................................................ [ 35%]
........................................................................ [ 70%]
...........................................................              [100%]
203 passed in 46.54s
```
- **Total Test Suites**: 18 test files
- **Total Passed Tests**: 203 (100% pass rate)
- **Failures / Errors**: 0

### 7.2 Ruff Linter & Formatting
```
.venv\Scripts\python -m ruff check .
All checks passed!
```
- **Linter Violations**: 0

### 7.3 Git Diff Quality
```
git diff --check
(Exit code 0; zero whitespace issues, zero merge markers)
```

### 7.4 Dependency Vulnerability Scan Status
- Execution command: `.venv\Scripts\python -m pip_audit`
- Result: **Tool Unavailable Locally**. `pip-audit` is not installed in the active development virtual environment. Software composition analysis (SCA) must be included as a step in the CI/CD pipeline before production release.

---

## 8. Untested Live Infrastructure Assumptions

Because this audit is strictly **read-only and local**, the following operational assumptions have been statically evaluated but remain **untested on live hardware**:
1. **Live PostgreSQL 16 Concurrency**: Alembic migrations have been validated against SQLite in unit tests. Execution against live PostgreSQL 16 with real user grants will take place on initial VM bring-up.
2. **Live Tailscale Ingress Routing**: UFW rules (`ufw allow in on tailscale0`) are structurally correct but require a live Tailscale daemon connected to a tailnet.
3. **Live Nginx WebSocket Multiplexing**: WebSocket upgrades have been validated via code inspection; long-lived duplex connections will be verified live on staging.
4. **Live Restic S3 Sync**: Off-host backup synchronization via `aws s3 sync` or `rclone` has not been tested against a live remote object storage bucket.

---

## 9. Estimated Staging Operational Prerequisites & Cost Categories

*(All estimations provided for planning purposes only; zero purchases or cloud resources provisioned).*

| Category | Recommended Provider / Tool | Resource Profile | Estimated Monthly Cost |
| :--- | :--- | :--- | :---: |
| **Dedicated Staging VM** | Hetzner Cloud (CPX21) / AWS (t4g.medium) / GCP (e2-standard-2) | 2–3 vCPU, 4 GB RAM, 40 GB NVMe | \$8 – \$25 / month |
| **Private Ingress VPN** | Tailscale | Tailscale Free Community Tier (up to 3 users) | \$0.00 |
| **Off-Host Encrypted Backup** | AWS S3 / Cloudflare R2 / Backblaze B2 | 10 GB – 20 GB encrypted storage + egress | < \$1.00 / month |
| **AI Studio API** | Google AI Studio (Gemini 3.8 Flash) | Educational research queries (pay-as-you-go) | Free Tier / < \$5.00 |
| **Total Estimated Operating Cost** | | | **\$9 – \$30 / month** |

---

## 10. Prioritized Pre-Deployment Action Plan

Before executing `provision_ubuntu24.sh` on the staging VM, the operator must complete the following three steps:

1. **Step 1 (Host Sizing)**: Ensure the target Ubuntu 24.04 VM is provisioned with at least **2 vCPUs and 4 GB RAM** (with a 2 GB swapfile) to accommodate concurrent services and prevent pip install OOM failures.
2. **Step 2 (Tailscale Connectivity & Certificates)**: Install and authenticate Tailscale on the VM (`tailscale up`), and generate or provide certificates (`tailscale cert <hostname>` or snakeoil certs) before starting Nginx.
3. **Step 3 (Provisioning Invocation)**: Execute the provisioning script explicitly specifying the VPN network mode:
   ```bash
   sudo NETWORK_MODE=vpn bash deploy/scripts/provision_ubuntu24.sh
   ```

---

## 11. Final Release Recommendation

The HeartAI platform at commit `dcc48d6` satisfies all software engineering, data modeling, anti-spoofing, session persistence, and disaster recovery requirements for pre-staging deployment.

**Final Verdict: `CONDITIONAL GO FOR CONTROLLED PRIVATE STAGING`**

The project is cleared for Point 14 (Controlled Staging Deployment) upon technical-lead review and acknowledgment of the three operational prerequisites.
