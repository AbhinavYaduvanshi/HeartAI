# HeartAI Backup, Disaster Recovery & Artifact Restoration Guide

**Project**: HeartAI — Cardiovascular Clinical Intelligence Platform  
**Target Audience**: Systems Administrators, Site Reliability Engineers, Database Administrators  
**Recovery Objectives**:
- **RTO (Recovery Time Objective)**: < 30 minutes
- **RPO (Recovery Point Objective)**: < 1 hour  

---

## 1. Backup Scope & Assets Inventory

A complete HeartAI disaster recovery snapshot encompasses three distinct asset classes:

1. **Stateful Database Records**:
   - `users`: Account credentials, active status, and server-verified informed consent timestamps.
   - `prediction_records`: Consent-gated prediction history with keyed HMAC-SHA256 input digests.
2. **Deterministic ML Artifacts & Governance Metadata**:
   - `models/best_model.joblib` (SHA-256: `5dc4...890`)
   - `models/preprocessing_pipeline.joblib` (SHA-256: `3a35...055`)
   - `models/model_metadata.json`
   - `models/feature_names.json`
3. **Environment Configuration & Cryptographic Keys**:
   - `.env` (contains `SECRET_KEY`, `TELEMETRY_HMAC_KEY`, `DATABASE_URL`).

---

## 2. Backup Schedules & Retention Policy

HeartAI implements a Grandfather-Father-Son (GFS) backup retention rotation:

| Backup Tier | Frequency | Destination | Retention Period |
| :--- | :--- | :--- | :--- |
| **Hourly WAL Archive** | Continuous / Hourly | Off-site S3/GCS bucket | 7 days |
| **Daily Full Backup** | Nightly at 02:00 UTC | Encrypted local backup disk + Cloud | 14 days |
| **Weekly Snapshot** | Sundays at 03:00 UTC | Off-site immutable storage (WORM) | 8 weeks |
| **Monthly Archive** | 1st of each month | Cold Glacier / Archive storage | 12 months |

---

## 3. Automated Backup Script (`/opt/heartai/scripts/backup.sh`)

Deploy this automated backup script via root cron:

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/var/backups/heartai/${BACKUP_DATE}"
APP_DIR="/opt/heartai"
RETENTION_DAYS=14

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting HeartAI backup to ${BACKUP_DIR}..."

# 1. PostgreSQL Database Dump (Custom compressed format)
echo "[$(date)] Exporting PostgreSQL database..."
pg_dump -U heartai_user -h localhost -d heartai_db -Fc -f "${BACKUP_DIR}/heartai_db_${BACKUP_DATE}.dump"

# 2. Archive Model Artifacts and Verification Manifest
echo "[$(date)] Archiving ML model artifacts..."
tar -czf "${BACKUP_DIR}/model_artifacts_${BACKUP_DATE}.tar.gz" -C "${APP_DIR}" \
    models/best_model.joblib \
    models/preprocessing_pipeline.joblib \
    models/model_metadata.json \
    models/feature_names.json

# 3. Archive Configuration (Encrypted via GPG)
echo "[$(date)] Archiving environment configuration..."
gpg --batch --yes --passphrase-file /etc/heartai_backup_passphrase.key \
    -c "${APP_DIR}/.env" -o "${BACKUP_DIR}/env_${BACKUP_DATE}.gpg"

# 4. Generate SHA-256 Checksums for Backup Bundle
cd "${BACKUP_DIR}"
sha256sum * > SHA256SUMS.txt

# 5. Clean up old local backups
find /var/backups/heartai/ -maxdepth 1 -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} +

echo "[$(date)] Backup completed successfully."
```

Configure in cron (`crontab -e`):
```cron
0 2 * * * /opt/heartai/scripts/backup.sh >> /var/log/heartai/backup.log 2>&1
```

---

## 4. Disaster Recovery & Restoration Procedures

### 4.1 Database Restoration
To restore the PostgreSQL database from a `.dump` archive:

```bash
# 1. Stop application server
sudo systemctl stop heartai.service

# 2. Drop active connections and restore database
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'heartai_db';"
sudo -u postgres dropdb heartai_db
sudo -u postgres createdb -O heartai_user heartai_db

# 3. Restore from compressed archive
pg_restore -U heartai_user -h localhost -d heartai_db -v "/var/backups/heartai/20261114_020000/heartai_db_20261114_020000.dump"
```

### 4.2 Model Artifact Restoration & Checksum Verification
If model files are lost or tampered with:

```bash
# 1. Extract artifacts to /opt/heartai
cd /opt/heartai
tar -xzf /var/backups/heartai/20261114_020000/model_artifacts_20261114_020000.tar.gz

# 2. Verify SHA-256 digests against known good baseline
python3 - << 'EOF'
import hashlib, json
from pathlib import Path

with open("models/model_metadata.json") as f:
    meta = json.load(f)

for path, expected_hash in [
    ("models/best_model.joblib", meta["sha256_checksum"]),
    ("models/preprocessing_pipeline.joblib", meta["preprocessing"]["sha256_checksum"])
]:
    actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    assert actual == expected_hash, f"FAIL: {path} hash mismatch!"
    print(f"VERIFIED: {path} matches expected SHA-256 ({actual})")
EOF
```

### 4.3 Service Restart and Validation
```bash
# Restart application service
sudo systemctl start heartai.service

# Check health endpoint
curl -s http://127.0.0.1:8000/health | jq .
```

---

## 5. Annual Disaster Recovery Drill Checklist

- [ ] Execute unannounced restore drill in staging VPC.
- [ ] Restore database dump from cold cloud storage.
- [ ] Verify user table counts match production baseline.
- [ ] Verify model checksum matches release manifest.
- [ ] Measure RTO and RPO against target SLA (< 30 min RTO, < 1 hr RPO).
- [ ] Document audit log of drill and archive with compliance records.
