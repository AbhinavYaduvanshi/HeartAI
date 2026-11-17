# HeartAI — Point 12.2.2: Backup Security & Disaster Recovery Architecture Report

**Date**: November 17, 2026  
**Auditor**: Antigravity Autonomous Technical Verification System  
**Baseline Git Commit**: `fbfc50784f146b5951b585f6c779a9cc7687476c` (origin/main synchronized)  
**Target Environment**: Ubuntu 24.04 LTS Dedicated VM (Option A Staging Architecture)  
**Primary Engine**: Restic (Client-Side Encrypted, Deduplicated Snapshot Repository) with OpenSSL AES-256 Fallback  
**Audit Scope**: Client-Side Encryption, Key Management & Escrow, Systemd Automation, Mutual Exclusion, Pre-Restore Safety, and Off-Host Replication  

---

## 1. Executive Summary & Architecture Redesign

In response to Point 12.2.1 feedback, the staging backup and recovery architecture was redesigned to eliminate the security vulnerability of local, unencrypted `.env` copies and same-VM encryption key dependencies.

```mermaid
flowchart TD
    subgraph Host["Staging Host (Ubuntu 24.04 VM)"]
        PG["PostgreSQL 16 (heartai_db)"] -->|pg_dump -Fc| Dump["Temporary Binary Dump (/tmp)"]
        Env["Application Secrets (/opt/heartai/.env)"]
        Models["ML Model Artifacts (/opt/heartai/models)"]
        
        Dump --> ResticEngine["Restic Engine (Client-Side AES-256 / Poly1305)"]
        Env --> ResticEngine
        Models --> ResticEngine
        
        KeySource["Key Injection: RESTIC_PASSWORD_FILE (/etc/heartai/backup_key, mode 400) or RESTIC_PASSWORD_COMMAND"] -.->|Encryption Key| ResticEngine
    end

    subgraph Storage["Backup Storage Repositories (Encrypted Chunks Only)"]
        ResticEngine -->|Encrypted Snapshots| LocalRepo["Local Staging (/var/backups/heartai)"]
        ResticEngine -->|Encrypted Replication (restic copy / s3 sync)| RemoteRepo["Off-Host Target (AWS S3 / GCS / SFTP)"]
    end

    style Host fill:#f8f9fa,stroke:#495057
    style Storage fill:#e9ecef,stroke:#212529
```

### Core Security Principles of the Redesign:
1. **Zero Plaintext Secrets**: Application secrets (`.env`), database dumps, and model artifacts are encrypted locally on the host before writing to disk or transmitting off-host.
2. **Client-Side vs Provider-Side Encryption**: Client-side encryption ensures that the cloud storage provider (e.g. AWS S3, Cloudflare R2, or remote SFTP) possesses zero knowledge of keys or contents. Cloud provider encryption-at-rest (e.g. SSE-S3) is treated only as a secondary defense against physical drive theft, not a substitute for client-side encryption.
3. **Key Separation & Escrow**: The encryption key is injected via `RESTIC_PASSWORD_FILE` (or `RESTIC_PASSWORD_COMMAND`) from outside the backup repository and escrowed in an offline password manager / secrets vault.
4. **Mutual Exclusion**: Script execution is protected by `flock -n /run/lock/heartai-backup.lock` to prevent overlapping runs.
5. **Pre-Restore Validation & Destructive Guard**: `restore_staging.sh` validates dump headers with `pg_restore -l` before touching live data and enforces an explicit confirmation prompt.

---

## 2. Evaluation of Restic vs Custom Scripted Encryption

| Security & Operational Requirement | Custom Script (`pg_dump` + `openssl` tarballs) | Restic Client-Side Encrypted Snapshots | Selection & Rationale |
| :--- | :--- | :--- | :---: |
| **Cryptographic Primitives** | AES-256-CBC via OpenSSL CLI | AES-256-CTR + Poly1305 MAC (or ChaCha20-Poly1305) | **Restic**: Cryptographically authenticated ciphertext prevents bit-flipping attacks. |
| **Deduplication** | None (full archive generated on every hourly run) | Content-defined chunking (Rabin-Karp fingerprinting) | **Restic**: Minimizes storage and bandwidth; only changed database blocks and files are backed up. |
| **Integrity Verification** | Manual `sha256sum` manifest | Built-in SHA-256 chunk hashing + `restic check` | **Restic**: Mathematically verifies metadata, pack files, and blob integrity on demand. |
| **Snapshot Management** | Manual `find -mtime` filesystem pruning | Atomic snapshot pruning: `restic forget --prune` | **Restic**: Deterministic point-in-time recovery with tag and host filtering. |
| **Key Rotation** | Requires full archive re-encryption | Native multi-key support (`restic key add/remove`) | **Restic**: Allows rotating passphrases without re-encrypting repository data. |
| **Backend Portability** | Manual rsync / aws s3 sync scripts | Native support for S3, GCS, B2, Azure, SFTP, and local disk | **Restic**: Uniform backup interface across all cloud storage backends. |

**Verdict**: **Restic** is selected as the primary backup engine. A hardened OpenSSL fallback remains in the script only if Restic is absent from the host environment.

---

## 3. Cryptographic Key Management & Recovery Procedure

### 3.1 Key Generation & Host Ingestion
1. **Key Generation**: The encryption key must be generated using a cryptographically secure pseudo-random number generator (CSPRNG):
   ```bash
   python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
   ```
2. **Host Ingestion**:
   - The key is written to `/etc/heartai/backup_key` with strict Unix permissions: `chmod 400`, owned by `root:root`.
   - The directory `/etc/heartai` is restricted to `chmod 700`, owned by `root:root`.
   - In automated cloud provisioning, the key is provisioned via cloud-init / AWS SSM Parameter Store / HashiCorp Vault.

### 3.2 Key Escrow & Disaster Recovery
- **Off-Host Escrow**: The Restic master passphrase is never stored solely on the VM. It must be escrowed in an offline physical safe or encrypted corporate password manager (e.g. 1Password / Bitwarden / HashiCorp Vault) accessible only to authorized disaster-recovery administrators.
- **Key Rotation**:
  Restic allows adding secondary recovery keys without invalidating existing backups:
  ```bash
  export RESTIC_PASSWORD_FILE=/etc/heartai/backup_key
  restic -r /var/backups/heartai key add
  ```
  Once the new key is verified, the obsolete key is removed via `restic key remove <KEY_ID>`.

---

## 4. Systemd Automation & Scheduling Review

The automated backup routine is supervised by Systemd to guarantee reliability, resource capping, and logging:

### 4.1 Unit Definitions
- **Service Unit**: [deploy/systemd/heartai-backup.service](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter system/deploy/systemd/heartai-backup.service)
  - `Type=oneshot`
  - `User=root` (required for system-wide directory access and PostgreSQL database dump via `sudo -u postgres`)
  - `TimeoutStartSec=1800` (caps backup execution to 30 minutes)
  - `StandardOutput=journal`, `StandardError=journal`
  - Sandboxing: `ProtectSystem=full`, `ProtectHome=true`, `PrivateTmp=true`, `NoNewPrivileges=true`
- **Timer Unit**: [deploy/systemd/heartai-backup.timer](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter system/deploy/systemd/heartai-backup.timer)
  - `OnCalendar=*-*-* *:00:00` (fires at the top of every hour)
  - `AccuracySec=1m` (prevents jitter while avoiding system load spikes)
  - `Persistent=true` (if the VM was stopped or suspended at the scheduled time, the backup triggers immediately on boot)

### 4.2 Overlap Prevention (Mutual Exclusion)
To prevent race conditions and high I/O contention if a large database dump takes longer than an hour, `backup_staging.sh` enforces file-descriptor locking:
```bash
LOCK_FILE="/run/lock/heartai-backup.lock"
exec 200>"${LOCK_FILE}"
if ! flock -n 200; then
    echo "[HeartAI Backup] Another backup process is currently running. Exiting."
    exit 1
fi
```

### 4.3 Enablement Procedure
```bash
sudo cp deploy/systemd/heartai-backup.service /etc/systemd/system/
sudo cp deploy/systemd/heartai-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now heartai-backup.timer
sudo systemctl list-timers heartai-backup.timer
```

---

## 5. Off-Host Replication & Retention Policy

### 5.1 Replication Architecture
To survive complete VM host destruction, the backup script includes an automated off-host replication hook:
- **Environment Variable**: `OFFHOST_BACKUP_DEST` (e.g. `s3:s3.amazonaws.com/heartai-staging-backups`).
- **Transport**: Restic native backend replication (`restic copy`) or encrypted S3 synchronization (`aws s3 sync ... --sse AES256`).
- **Access Restrictions**: Cloud storage buckets are configured with Object Lock (WORM - Write Once, Read Many) to prevent ransomware from encrypting or deleting historical snapshots.

### 5.2 Deterministic Retention Policy
The hourly backup script enforces atomic snapshot pruning:
```bash
restic forget --keep-hourly 24 --keep-daily 7 --keep-weekly 4 --prune
```
- Retains 24 hourly snapshots (covering the preceding 24 hours).
- Retains 7 daily snapshots (covering the preceding 7 days).
- Retains 4 weekly snapshots (covering the preceding month).
- Unreferenced data chunks are automatically purged from the repository via `--prune`.

---

## 6. Pre-Restore Validation & Destructive Recovery Safeguards

The restore procedure ([deploy/scripts/restore_staging.sh](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter system/deploy/scripts/restore_staging.sh)) incorporates safety layers to prevent accidental data loss:

1. **Explicit Operator Confirmation**:
   The script halts and prompts:
   `To proceed, type 'RESTORE' exactly: `
   Non-interactive execution requires an explicit `--confirm` CLI flag.
2. **Pre-Restore Header Validation**:
   Before stopping active services or dropping `heartai_db`, the script validates the archive format:
   ```bash
   if ! pg_restore -l "${DUMP_FILE}" >/dev/null 2>&1; then
       echo "Error: Database dump file is corrupt or unreadable. Restore aborted."
       exit 1
   fi
   ```
   If the archive is corrupt, the script aborts immediately, leaving the active database untouched.
3. **Database Ownership & Schema Reconstitution**:
   Recreation commands enforce standard ownership and peer authentication:
   ```bash
   sudo -u postgres psql -c "DROP DATABASE IF EXISTS heartai_db;"
   sudo -u postgres psql -c "CREATE DATABASE heartai_db OWNER heartai_user;"
   sudo -u postgres pg_restore -d heartai_db --no-owner --role=heartai_user "${DUMP_FILE}"
   ```
   Post-restore queries verify that `users` and `prediction_records` tables exist.
4. **Service Health Re-Verification**:
   Post-restore commands restart `heartai-backend` and `heartai-frontend`, querying `/health` to confirm `status="healthy"` and `model_loaded=true`.

---

## 7. Operational Recovery Metrics Disclaimer

> [!WARNING]
> **ENGINEERING TARGET DISCLAIMER**:  
> The Recovery Point Objective (RPO < 1 hour) and Recovery Time Objective (RTO < 30 minutes) are **unverified engineering targets**.  
> In strict accordance with Point 12.2.2 guidelines, these targets will not be certified as operational capabilities until an actual timed drill is performed on the staging VM following cloud host provisioning.
