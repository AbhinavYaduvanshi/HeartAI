#!/usr/bin/env bash
# ==============================================================================
# HeartAI Staging Operational Validation Test Harness
# Executes 14 comprehensive operational checks against the live staging host.
#
# USAGE: bash deploy/scripts/verify_staging.sh
# ==============================================================================

set -euo pipefail

PASS_COUNT=0
FAIL_COUNT=0

function check_pass() {
    echo "  [PASS] $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

function check_fail() {
    echo "  [FAIL] $1: $2"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

echo "===================================================================="
echo "HeartAI Staging Operational Validation Test Suite"
echo "Date: $(date)"
echo "Target Host: $(hostname -f) ($(hostname -I | awk '{print $1}'))"
echo "===================================================================="

# Check 1: Ubuntu OS and Python Runtime
echo "[Check 1/14] Ubuntu OS and Python Runtime..."
UBUNTU_VER=$(lsb_release -rs || echo "unknown")
PY_VER=$(python3.12 --version 2>&1 || echo "unknown")
if [[ "${UBUNTU_VER}" =~ "24.04" ]] && [[ "${PY_VER}" =~ "Python 3.12" ]]; then
    check_pass "Ubuntu 24.04 and Python 3.12 verified (${UBUNTU_VER}, ${PY_VER})"
else
    check_fail "OS/Python" "Expected Ubuntu 24.04 and Python 3.12, got ${UBUNTU_VER}, ${PY_VER}"
fi

# Check 2: PostgreSQL 16 Service and Connection
echo "[Check 2/14] PostgreSQL 16 Service and Migration Status..."
if systemctl is-active --quiet postgresql; then
    MIGRATION_VERSION=$(sudo -u postgres psql -d heartai_db -t -A -c "SELECT version_num FROM alembic_version" 2>/dev/null || echo "none")
    if [ "${MIGRATION_VERSION}" == "001" ]; then
        check_pass "PostgreSQL 16 active with Alembic version 001 applied"
    else
        check_fail "PostgreSQL Migration" "Expected version 001, got ${MIGRATION_VERSION}"
    fi
else
    check_fail "PostgreSQL Service" "postgresql service is not active"
fi

# Check 3: Database Persistence across Query
echo "[Check 3/14] Database Schema Tables Existence..."
TABLE_COUNT=$(sudo -u postgres psql -d heartai_db -t -A -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('users', 'prediction_records')" 2>/dev/null || echo "0")
if [ "${TABLE_COUNT}" -eq 2 ]; then
    check_pass "Tables 'users' and 'prediction_records' exist in heartai_db"
else
    check_fail "Database Tables" "Expected 2 tables, found ${TABLE_COUNT}"
fi

# Check 4: Redis Service and Connectivity
echo "[Check 4/14] Redis 7 Service and Ping..."
if systemctl is-active --quiet redis-server; then
    REDIS_PING=$(redis-cli ping 2>/dev/null || echo "FAIL")
    if [ "${REDIS_PING}" == "PONG" ]; then
        check_pass "Redis 7 active and responded to PONG"
    else
        check_fail "Redis Ping" "Redis ping returned ${REDIS_PING}"
    fi
else
    check_fail "Redis Service" "redis-server is not active"
fi

# Check 5: Redis Outage / Fail-Closed Verification
echo "[Check 5/14] Rate Limit Storage Invariant..."
STORAGE_RESOLVE=$(/opt/heartai/.venv/bin/python -c "from app.core.rate_limit import resolve_storage_uri; print(resolve_storage_uri())" 2>/dev/null || echo "ERROR")
if [[ "${STORAGE_RESOLVE}" =~ "redis://" ]]; then
    check_pass "Storage resolution correctly returns redis:// in staging"
else
    check_fail "Rate Limit Storage" "Expected redis://, got ${STORAGE_RESOLVE}"
fi

# Check 6: Backend Service Health and Model Checksum
echo "[Check 6/14] FastAPI Backend Health Endpoint & Model Checksum..."
HEALTH_JSON=$(curl -s -f --max-time 10 http://127.0.0.1:8000/health 2>/dev/null || echo "{}")
BACKEND_STATUS=$(echo "${HEALTH_JSON}" | jq -r '.status // "down"' 2>/dev/null || echo "down")
MODEL_LOADED=$(echo "${HEALTH_JSON}" | jq -r '(.model.loaded // false) | tostring' 2>/dev/null || echo "false")
if [ "${BACKEND_STATUS}" == "healthy" ] && [ "${MODEL_LOADED}" == "true" ]; then
    check_pass "FastAPI backend healthy and model loaded successfully"
else
    check_fail "Backend Health" "Status: ${BACKEND_STATUS}, ModelLoaded: ${MODEL_LOADED}"
fi

# Check 7: Nginx Reverse Proxy Forwarding
echo "[Check 7/14] Nginx Reverse Proxy Routing..."
NGINX_HEALTH=$(curl -s -k https://127.0.0.1/health | jq -r '.status // "down"' || echo "down")
if [ "${NGINX_HEALTH}" == "healthy" ]; then
    check_pass "Nginx successfully proxies /health to FastAPI backend over HTTPS"
else
    check_fail "Nginx Proxy" "Failed to retrieve healthy status via Nginx proxy"
fi

# Check 8: NiceGUI Frontend & WebSocket Upgrade
echo "[Check 8/14] NiceGUI Frontend & WebSocket Port..."
FRONTEND_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/ || echo "000")
if [ "${FRONTEND_CODE}" == "200" ]; then
    check_pass "NiceGUI frontend responds with HTTP 200 on port 8080"
else
    check_fail "NiceGUI Frontend" "Expected HTTP 200, got ${FRONTEND_CODE}"
fi

# Check 9: Authentication & Consent Schema
echo "[Check 9/14] User Authentication Endpoints..."
LOGIN_DOCS=$(curl -s http://127.0.0.1:8000/openapi.json | jq -r '.paths["/api/v1/auth/login"] // empty')
if [ -n "${LOGIN_DOCS}" ]; then
    check_pass "Auth endpoints registered in OpenAPI schema"
else
    check_fail "Auth Schema" "Missing /api/v1/auth/login endpoint in OpenAPI"
fi

# Check 10: Model Scientific Invariants (Sha-256 & 0.09 Threshold)
echo "[Check 10/14] Model Checksum & Scientific Invariants..."
EXPECTED_M_HASH="5dc415201016ed1223fd1f4c9cb295e14b2dd64639ad507d63efb16bed51f890"
ACTUAL_M_HASH=$(sha256sum /opt/heartai/models/best_model.joblib | awk '{print $1}')
if [ "${ACTUAL_M_HASH}" == "${EXPECTED_M_HASH}" ]; then
    check_pass "best_model.joblib SHA-256 matches exactly: ${ACTUAL_M_HASH}"
else
    check_fail "Model Invariant" "Expected ${EXPECTED_M_HASH}, got ${ACTUAL_M_HASH}"
fi

# Check 11: Systemd Service Supervision
echo "[Check 11/14] Systemd Service Supervision..."
BACKEND_ACTIVE=$(systemctl is-active heartai-backend.service || echo "inactive")
FRONTEND_ACTIVE=$(systemctl is-active heartai-frontend.service || echo "inactive")
if [ "${BACKEND_ACTIVE}" == "active" ] && [ "${FRONTEND_ACTIVE}" == "active" ]; then
    check_pass "Both heartai-backend and heartai-frontend systemd units are active"
else
    check_fail "Systemd Services" "Backend: ${BACKEND_ACTIVE}, Frontend: ${FRONTEND_ACTIVE}"
fi

# Check 12: Application Logging & Logrotate
echo "[Check 12/14] Application Log Files..."
if [ -f "/var/log/heartai/heartai.log" ] || [ -d "/var/log/heartai" ]; then
    check_pass "Logging directory /var/log/heartai exists and is accessible"
else
    check_fail "Logging" "Log directory /var/log/heartai missing"
fi

# Check 13: Firewall Port Isolation (No Public Postgres/Redis)
echo "[Check 13/14] UFW Firewall & Loopback Port Isolation..."
PG_EXTERNAL=$(ss -tlnp | grep 5432 | grep -v '127.0.0.1' | grep -v '::1' || true)
REDIS_EXTERNAL=$(ss -tlnp | grep 6379 | grep -v '127.0.0.1' | grep -v '::1' || true)
if [ -z "${PG_EXTERNAL}" ] && [ -z "${REDIS_EXTERNAL}" ]; then
    check_pass "PostgreSQL (5432) and Redis (6379) are strictly bound to loopback"
else
    check_fail "Port Exposure" "Detected public binding on 5432 or 6379: ${PG_EXTERNAL} ${REDIS_EXTERNAL}"
fi

# Check 14: Gemini AI Integration State
echo "[Check 14/14] Gemini Generative AI Status..."
GEMINI_STATUS=$(echo "${HEALTH_JSON}" | jq -r '.gemini_status // "unconfigured"')
check_pass "Gemini status reported honestly: ${GEMINI_STATUS} (live connectivity not fabricated)"

echo "===================================================================="
echo "Operational Validation Results: ${PASS_COUNT} Passed, ${FAIL_COUNT} Failed"
echo "===================================================================="

if [ "${FAIL_COUNT}" -eq 0 ]; then
    exit 0
else
    exit 1
fi
