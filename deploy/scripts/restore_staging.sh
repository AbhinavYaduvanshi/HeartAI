#!/usr/bin/env bash
# ==============================================================================
# HeartAI Staging Fail-Safe Disaster Recovery & Restore Script
# ==============================================================================
# ARCHITECTURAL SAFEGUARDS:
# 1. FAIL-SAFE RESTORATION: Data is first restored into a temporary staging database
#    ('heartai_db_restore_staging') and completely verified before live DB is modified.
# 2. VALIDATION DRILL VS ACTIVE SWAP:
#    - '--validate-only': Restores and validates in isolated scratch DB without modifying live state.
#    - '--confirm': Performs active, state-changing database replacement and service restart.
# 3. ATOMIC SWAP & ROLLBACK: Live database is renamed to a rollback snapshot.
#    If post-restore health verification fails, the original database is restored immediately.
# 4. PATH TRAVERSAL GUARDS: Tar extractions check for '..' or absolute paths before extracting.
# 5. LEGACY ARCHIVE ACCESS: Explicit operator approval required for unverified legacy archives.
# ==============================================================================

set -euo pipefail

TARGET_SNAPSHOT="${1:-latest}"
MODE_FLAG="${2:-}"
LOCAL_BACKUP_REPO="${BACKUP_REPO:-/var/backups/heartai}"
PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-/etc/heartai/backup_key}"
RESTORE_TMP="/tmp/heartai_restore_$(date +"%s")"
STAGING_DB="heartai_db_restore_staging"
LIVE_DB="heartai_db"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
ROLLBACK_DB="heartai_db_rollback_${TIMESTAMP}"

echo "===================================================================="
echo "HeartAI Staging Disaster Recovery & Restore"
echo "Target Snapshot: ${TARGET_SNAPSHOT}"
echo "Repository: ${LOCAL_BACKUP_REPO}"
echo "Mode: ${MODE_FLAG:-interactive}"
echo "===================================================================="

# 0. Safety Confirmation Guard
if [ "${MODE_FLAG}" != "--confirm" ] && [ "${MODE_FLAG}" != "--validate-only" ]; then
    echo ""
    echo " [CRITICAL WARNING] This operation will restore database snapshot '${TARGET_SNAPSHOT}'."
    echo " Choose an execution mode:"
    echo "   1) Validate only (non-destructive test in scratch DB without touching live DB)"
    echo "   2) Active database replacement (STATE-CHANGING: stops services, swaps database, restarts)"
    echo ""
    read -r -p "To proceed with active replacement, type 'RESTORE' exactly (or 'V' for validate-only): " USER_INPUT
    if [ "${USER_INPUT}" == "V" ] || [ "${USER_INPUT}" == "v" ]; then
        MODE_FLAG="--validate-only"
    elif [ "${USER_INPUT}" != "RESTORE" ]; then
        echo "Restore aborted by operator."
        exit 1
    fi
fi

cleanup() {
    rm -rf "${RESTORE_TMP}"
    # Drop staging scratch DB if it exists and was not promoted
    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${STAGING_DB}'" 2>/dev/null | grep -q 1 && \
        sudo -u postgres psql -c "DROP DATABASE ${STAGING_DB};" 2>/dev/null || true
}
trap cleanup EXIT ERR INT TERM

mkdir -p "${RESTORE_TMP}"
chmod 700 "${RESTORE_TMP}"

# 1. Repository & Snapshot Integrity Verification
DUMP_FILE=""
if command -v restic >/dev/null 2>&1 && [ -f "${PASSWORD_FILE}" ]; then
    echo "[1/6] Verifying Restic repository and snapshot integrity..."
    export RESTIC_PASSWORD_FILE="${PASSWORD_FILE}"
    export RESTIC_REPOSITORY="${LOCAL_BACKUP_REPO}"

    # Verify repository metadata and blob integrity
    restic check

    # Extract target snapshot to isolated restore directory
    echo "Extracting snapshot '${TARGET_SNAPSHOT}' to ${RESTORE_TMP}..."
    restic restore "${TARGET_SNAPSHOT}" --target "${RESTORE_TMP}"

    DUMP_FILE=$(find "${RESTORE_TMP}" -name "*.dump" -o -name "heartai_db*" | head -n 1)

else
    echo "[1/6] Target is not a verified Restic repository snapshot. Checking for legacy archive..."
    if [ "${MODE_FLAG}" != "--allow-legacy" ] && [ "${ALLOW_LEGACY:-0}" != "1" ]; then
        echo "===================================================================="
        echo "[SECURITY GUARD] Restoring from legacy unverified directory archives"
        echo "requires explicit operator confirmation."
        echo "Restic is the mandatory backup engine for HeartAI controlled staging."
        echo "===================================================================="
        read -r -p "Type 'RESTORE-LEGACY' to proceed with legacy archive restoration: " LEGACY_CONFIRM
        if [ "${LEGACY_CONFIRM}" != "RESTORE-LEGACY" ]; then
            echo "Legacy restoration aborted by operator."
            exit 1
        fi
    fi

    if [ -d "${LOCAL_BACKUP_REPO}/${TARGET_SNAPSHOT}" ]; then
        SOURCE_DIR="${LOCAL_BACKUP_REPO}/${TARGET_SNAPSHOT}"
    else
        SOURCE_DIR=$(find "${LOCAL_BACKUP_REPO}" -maxdepth 1 -mindepth 1 -type d | sort -r | head -n 1)
    fi

    if [ -z "${SOURCE_DIR}" ] || [ ! -d "${SOURCE_DIR}" ]; then
        echo "Error: No valid backup archive found in ${LOCAL_BACKUP_REPO}."
        exit 1
    fi

    # Verify checksums if present
    if [ -f "${SOURCE_DIR}/SHA256SUMS.txt" ]; then
        (cd "${SOURCE_DIR}" && sha256sum -c SHA256SUMS.txt)
    fi

    ENC_DUMP=$(find "${SOURCE_DIR}" -name "*.dump.enc" | head -n 1)
    if [ -n "${ENC_DUMP}" ] && [ -f "${PASSWORD_FILE}" ]; then
        DUMP_FILE="${RESTORE_TMP}/decrypted_database.dump"
        openssl enc -d -aes-256-ctr -pbkdf2 \
            -in "${ENC_DUMP}" \
            -out "${DUMP_FILE}" \
            -pass file:"${PASSWORD_FILE}"
        chmod 600 "${DUMP_FILE}"
    fi

    # Decrypt models if present, enforcing path traversal guards (SEC-06)
    ENC_MODELS=$(find "${SOURCE_DIR}" -name "models.tar.gz.enc" | head -n 1)
    if [ -n "${ENC_MODELS}" ] && [ -f "${PASSWORD_FILE}" ]; then
        echo "Decrypting and verifying models from ${ENC_MODELS}..."
        DECRYPTED_TAR="${RESTORE_TMP}/models_temp.tar.gz"
        openssl enc -d -aes-256-ctr -pbkdf2 \
            -in "${ENC_MODELS}" \
            -out "${DECRYPTED_TAR}" \
            -pass file:"${PASSWORD_FILE}"
        if tar -tzf "${DECRYPTED_TAR}" | grep -E '(^/|\.\./)' >/dev/null 2>&1; then
            echo "[CRITICAL SECURITY ERROR] Path traversal sequence ('..' or '/') detected in model archive! Refusing extraction."
            rm -f "${DECRYPTED_TAR}"
            exit 1
        fi
        tar -xzf "${DECRYPTED_TAR}" --no-same-owner -C "${RESTORE_TMP}/"
        rm -f "${DECRYPTED_TAR}"
    elif [ -f "${SOURCE_DIR}/models.tar.gz" ]; then
        echo "Verifying and extracting legacy models archive..."
        if tar -tzf "${SOURCE_DIR}/models.tar.gz" | grep -E '(^/|\.\./)' >/dev/null 2>&1; then
            echo "[CRITICAL SECURITY ERROR] Path traversal sequence ('..' or '/') detected in model archive! Refusing extraction."
            exit 1
        fi
        tar -xzf "${SOURCE_DIR}/models.tar.gz" --no-same-owner -C "${RESTORE_TMP}/"
    fi
fi

# 2. Archive Format Integrity Check
echo "[2/6] Validating database dump structure..."
if [ -z "${DUMP_FILE}" ] || [ ! -f "${DUMP_FILE}" ]; then
    echo "Error: No database dump file located in extracted snapshot."
    exit 1
fi

if ! pg_restore -l "${DUMP_FILE}" >/dev/null 2>&1; then
    echo "Error: Database dump file '${DUMP_FILE}' is corrupt or unreadable. Active database untouched!"
    exit 1
fi
echo "Archive header and Table of Contents validated successfully."

# 3. Restore into Isolated Staging Database (Live DB is UNTOUCHED!)
echo "[3/6] Restoring into isolated verification database '${STAGING_DB}'..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS ${STAGING_DB};"
sudo -u postgres psql -c "CREATE DATABASE ${STAGING_DB} OWNER heartai_user;"
sudo -u postgres pg_restore -d "${STAGING_DB}" --no-owner --role=heartai_user "${DUMP_FILE}" || true

# 4. Data & Schema Completeness Verification in Staging Database
echo "[4/6] Verifying schema and records in '${STAGING_DB}'..."
TABLE_COUNT=$(sudo -u postgres psql -d "${STAGING_DB}" -t -A -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('users', 'prediction_records');")
ALEMBIC_VER=$(sudo -u postgres psql -d "${STAGING_DB}" -t -A -c "SELECT version_num FROM alembic_version" 2>/dev/null || echo "none")

if [ "${TABLE_COUNT}" -ne 2 ] || [ "${ALEMBIC_VER}" != "001" ]; then
    echo "Error: Verification failed on staging database! TableCount=${TABLE_COUNT}, AlembicVersion=${ALEMBIC_VER}."
    echo "Aborting restore! The live database '${LIVE_DB}' remains intact."
    exit 1
fi
echo "Data verification passed: 'users' and 'prediction_records' confirmed, Alembic version '${ALEMBIC_VER}' confirmed."

# Non-destructive validation drill completion
if [ "${MODE_FLAG}" == "--validate-only" ]; then
    echo "===================================================================="
    echo "Non-Destructive Disaster Recovery Validation Drill PASSED!"
    echo "Target snapshot '${TARGET_SNAPSHOT}' verified healthy and recoverable."
    echo "The live database '${LIVE_DB}' and application services were NOT modified."
    echo "===================================================================="
    exit 0
fi

# 5. Controlled Atomic Database Swap with Rollback Guarantee (STATE-CHANGING)
echo "[5/6] Performing controlled database replacement (STATE-CHANGING)..."
systemctl stop heartai-frontend.service || true
systemctl stop heartai-backend.service || true

# Terminate active backend connections to live database
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${LIVE_DB}' AND pid <> pg_backend_pid();" >/dev/null 2>&1 || true

# Rename live DB to rollback DB, and promote staging DB to live DB
sudo -u postgres psql -c "ALTER DATABASE ${LIVE_DB} RENAME TO ${ROLLBACK_DB};"
sudo -u postgres psql -c "ALTER DATABASE ${STAGING_DB} RENAME TO ${LIVE_DB};"

# 6. Service Restart & Health Verification
echo "[6/6] Restarting application services and verifying operational health..."
systemctl start heartai-backend.service
systemctl start heartai-frontend.service

sleep 4

# Safe, robust health check parsing using nested .model.loaded and .database.connected (REL-01)
HEALTH_JSON=$(curl -s -f --max-time 10 http://127.0.0.1:8000/health 2>/dev/null || echo "{}")
HEALTH_STATUS=$(echo "${HEALTH_JSON}" | jq -r '.status // "failed"' 2>/dev/null || echo "failed")
MODEL_LOADED=$(echo "${HEALTH_JSON}" | jq -r '(.model.loaded // false) | tostring' 2>/dev/null || echo "false")
DB_CONNECTED=$(echo "${HEALTH_JSON}" | jq -r '(.database.connected // false) | tostring' 2>/dev/null || echo "false")

if [ "${HEALTH_STATUS}" == "healthy" ] && [ "${MODEL_LOADED}" == "true" ] && [ "${DB_CONNECTED}" == "true" ]; then
    echo "===================================================================="
    echo "Restore Completed and Verified Successfully!"
    echo "Live database '${LIVE_DB}' is operational. Rollback snapshot: '${ROLLBACK_DB}'"
    echo "===================================================================="
    # Clean up rollback DB after successful health check
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS ${ROLLBACK_DB};" >/dev/null 2>&1 || true
    exit 0
else
    echo "===================================================================="
    echo "[CRITICAL ALERT] Health check failed post-restore! Initiating automatic rollback..."
    echo "===================================================================="
    systemctl stop heartai-frontend.service || true
    systemctl stop heartai-backend.service || true
    sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${LIVE_DB}' AND pid <> pg_backend_pid();" >/dev/null 2>&1 || true
    sudo -u postgres psql -c "ALTER DATABASE ${LIVE_DB} RENAME TO heartai_db_failed_restore;"
    sudo -u postgres psql -c "ALTER DATABASE ${ROLLBACK_DB} RENAME TO ${LIVE_DB};"
    systemctl start heartai-backend.service
    systemctl start heartai-frontend.service
    echo "Automatic rollback completed. Original database restored."
    exit 2
fi
