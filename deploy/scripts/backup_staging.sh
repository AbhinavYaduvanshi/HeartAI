#!/usr/bin/env bash
# ==============================================================================
# HeartAI Staging Backup Script (Client-Side Encrypted via Restic)
# ==============================================================================
# ARCHITECTURAL INVARIANTS:
# 1. STREAMING PIPELINE: The streaming pipeline does not intentionally write
#    plaintext database dump files to persistent storage; data streams directly
#    from pg_dump stdout into the encryption engine (Restic stdin snapshot).
# 2. CLIENT-SIDE ENCRYPTION: AES-256-CTR with Poly1305 MAC (Restic AEAD).
# 3. EXCLUSIVE ENGINE: Restic is the sole supported backup engine for controlled
#    staging. Silent fallback to unencrypted or unauthenticated ciphers is prohibited.
# 4. KEY SEPARATION & LIMITATIONS: Passphrase loaded from /etc/heartai/backup_key (chmod 400).
#    Root compromise of the host exposes the key; off-host escrow supports DR.
# 5. MUTUAL EXCLUSION: flock prevents overlapping backup runs.
# ==============================================================================

set -euo pipefail

LOCK_FILE="/run/lock/heartai-backup.lock"
exec 200>"${LOCK_FILE}"
if ! flock -n 200; then
    echo "[HeartAI Backup] Another backup process is currently running. Exiting."
    exit 1
fi

TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
LOCAL_BACKUP_REPO="${BACKUP_REPO:-/var/backups/heartai}"
DB_NAME="heartai_db"
PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-/etc/heartai/backup_key}"

# 0. Fail-Closed Cryptographic Pre-flight Checks (SEC-06)
if ! command -v restic >/dev/null 2>&1; then
    echo "===================================================================="
    echo "[CRITICAL ERROR] Restic executable not found in PATH!"
    echo "Restic is the mandatory encryption engine for HeartAI backups."
    echo "Silent fallback to unverified ciphers is prohibited in controlled staging."
    echo "Remediation: sudo apt-get update && sudo apt-get install -y restic"
    echo "===================================================================="
    exit 1
fi

if [ ! -f "${PASSWORD_FILE}" ]; then
    echo "===================================================================="
    echo "[CRITICAL ERROR] Mandatory encryption key file not found at:"
    echo "  ${PASSWORD_FILE}"
    echo "Backups cannot proceed without verified encryption credentials."
    echo "Remediation: Initialize /etc/heartai/backup_key with chmod 400 permissions."
    echo "===================================================================="
    exit 1
fi

# Volatile RAM scratch directory (shm) for temporary metadata manifests only
if [ -d "/dev/shm" ] && [ -w "/dev/shm" ]; then
    SECURE_TMP_DIR=$(mktemp -d -p /dev/shm heartai_backup_manifest_XXXXXX)
else
    SECURE_TMP_DIR=$(mktemp -d /tmp/heartai_backup_manifest_XXXXXX)
fi
chmod 700 "${SECURE_TMP_DIR}"

# Guaranteed cleanup trap for manifests
cleanup() {
    if [ -d "${SECURE_TMP_DIR}" ]; then
        rm -rf "${SECURE_TMP_DIR}"
    fi
}
trap cleanup EXIT ERR INT TERM

echo "===================================================================="
echo "[HeartAI Backup] Starting streaming encrypted backup at ${TIMESTAMP}"
echo "===================================================================="

# 1. Generate model artifacts manifest
(cd /opt/heartai/models && sha256sum best_model.joblib preprocessing_pipeline.joblib model_metadata.json > "${SECURE_TMP_DIR}/models_sha256.txt")

# 2. Client-Side Encrypted Backup Execution via Restic
echo "[1/3] Executing Restic client-side encrypted backup (AES-256-CTR + Poly1305)..."
export RESTIC_PASSWORD_FILE="${PASSWORD_FILE}"
export RESTIC_REPOSITORY="${LOCAL_BACKUP_REPO}"

# Initialize repository if not already present
if ! restic rev-list --all >/dev/null 2>&1; then
    echo "Initializing new Restic repository at ${RESTIC_REPOSITORY}..."
    mkdir -p "${RESTIC_REPOSITORY}"
    restic init
fi

# STREAM PostgreSQL dump directly into Restic stdin snapshot (NO PLAINTEXT DISK WRITES!)
echo "Streaming PostgreSQL database '${DB_NAME}' into Restic stdin snapshot..."
sudo -u postgres pg_dump -Fc "${DB_NAME}" | restic backup \
    --stdin \
    --stdin-filename "heartai_db_${TIMESTAMP}.dump" \
    --tag "staging,heartai,database,${TIMESTAMP}" \
    --host "$(hostname)"

# Snapshot application configuration and models directly from source (encrypted in-flight)
echo "Snapshotting application configuration and ML models..."
restic backup \
    --tag "staging,heartai,app_config,${TIMESTAMP}" \
    --host "$(hostname)" \
    "${SECURE_TMP_DIR}/models_sha256.txt" \
    /opt/heartai/.env \
    /opt/heartai/models

# Prune according to retention policy: 24 hourly, 7 daily, 4 weekly
echo "Enforcing retention policy..."
restic forget --keep-hourly 24 --keep-daily 7 --keep-weekly 4 --prune

# Verify repository integrity
echo "Verifying Restic repository integrity..."
restic check --read-data-subset=10%

echo "Restic encrypted snapshot successfully stored in ${RESTIC_REPOSITORY}."

# 3. Off-Host Synchronization Hook (Encrypted blobs only)
if [ -n "${OFFHOST_BACKUP_DEST:-}" ]; then
    echo "[2/3] Synchronizing encrypted repository to off-host target: ${OFFHOST_BACKUP_DEST}..."
    if command -v aws >/dev/null 2>&1; then
        aws s3 sync "${LOCAL_BACKUP_REPO}" "${OFFHOST_BACKUP_DEST}" --sse AES256 --delete
    elif command -v rclone >/dev/null 2>&1; then
        rclone sync "${LOCAL_BACKUP_REPO}" "${OFFHOST_BACKUP_DEST}"
    fi
fi

echo "===================================================================="
echo "[HeartAI Backup] Encrypted backup completed successfully at $(date)"
echo "===================================================================="

# 3. Off-Host Synchronization Hook (Encrypted blobs only)
if [ -n "${OFFHOST_BACKUP_DEST:-}" ]; then
    echo "[2/3] Synchronizing encrypted repository to off-host target: ${OFFHOST_BACKUP_DEST}..."
    if command -v aws >/dev/null 2>&1; then
        aws s3 sync "${LOCAL_BACKUP_REPO}" "${OFFHOST_BACKUP_DEST}" --sse AES256 --delete
    elif command -v rclone >/dev/null 2>&1; then
        rclone sync "${LOCAL_BACKUP_REPO}" "${OFFHOST_BACKUP_DEST}"
    fi
fi

echo "===================================================================="
echo "[HeartAI Backup] Encrypted backup completed successfully at $(date)"
echo "===================================================================="
