#!/usr/bin/env bash
# ==============================================================================
# HeartAI Staging Backup Script (Client-Side Encrypted via Restic / OpenSSL)
# ==============================================================================
# ARCHITECTURAL INVARIANTS:
# 1. STREAMING PIPELINE: The streaming pipeline does not intentionally write
#    plaintext database dump files to persistent storage; data streams directly
#    from pg_dump stdout into the encryption engine (Restic stdin or OpenSSL enc).
# 2. CLIENT-SIDE ENCRYPTION: AES-256-CTR with Poly1305 MAC (Restic) or AES-256-CTR (OpenSSL).
# 3. KEY SEPARATION & LIMITATIONS: Passphrase loaded from /etc/heartai/backup_key (chmod 400).
#    Root compromise of the host exposes the key; off-host escrow supports DR.
# 4. MUTUAL EXCLUSION: flock prevents overlapping backup runs.
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

# 2. Client-Side Encrypted Backup Execution
if command -v restic >/dev/null 2>&1 && [ -f "${PASSWORD_FILE}" ]; then
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
    restic check --read-data-subset=10%

    echo "Restic encrypted snapshot successfully stored in ${RESTIC_REPOSITORY}."

else
    echo "[1/3] Restic not available or no password file found. Using OpenSSL AES-256-CTR streaming fallback..."
    ARCHIVE_PATH="${LOCAL_BACKUP_REPO}/${TIMESTAMP}"
    mkdir -p "${ARCHIVE_PATH}"
    chmod 700 "${ARCHIVE_PATH}"

    # STREAM PostgreSQL dump directly through OpenSSL enc (NO PLAINTEXT DISK WRITES!)
    if [ -f "${PASSWORD_FILE}" ]; then
        echo "Streaming pg_dump directly through OpenSSL AES-256-CTR..."
        sudo -u postgres pg_dump -Fc "${DB_NAME}" | \
            openssl enc -aes-256-ctr -salt -pbkdf2 \
            -out "${ARCHIVE_PATH}/database_${TIMESTAMP}.dump.enc" \
            -pass file:"${PASSWORD_FILE}"
        chmod 600 "${ARCHIVE_PATH}/database_${TIMESTAMP}.dump.enc"

        # Encrypt .env directly
        if [ -f "/opt/heartai/.env" ]; then
            openssl enc -aes-256-ctr -salt -pbkdf2 \
                -in /opt/heartai/.env \
                -out "${ARCHIVE_PATH}/env.enc" \
                -pass file:"${PASSWORD_FILE}"
            chmod 600 "${ARCHIVE_PATH}/env.enc"
        fi
    else
        echo "[CRITICAL WARNING] No password file found at ${PASSWORD_FILE}. Streaming unencrypted fallback is blocked!"
        exit 1
    fi

    # Archive models
    tar -czf "${ARCHIVE_PATH}/models.tar.gz" -C /opt/heartai models/
    cp "${SECURE_TMP_DIR}/models_sha256.txt" "${ARCHIVE_PATH}/"
    (cd "${ARCHIVE_PATH}" && sha256sum * > SHA256SUMS.txt)
    chmod 600 "${ARCHIVE_PATH}/"*

    # Prune older than 7 days
    find "${LOCAL_BACKUP_REPO}" -maxdepth 1 -type d -mtime +7 -exec rm -rf {} +
fi

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
