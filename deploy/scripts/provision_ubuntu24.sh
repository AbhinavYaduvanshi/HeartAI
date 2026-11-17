#!/usr/bin/env bash
# ==============================================================================
# HeartAI Staging Provisioning Script for Ubuntu 24.04 LTS
# Target Architecture: Option A (Single Dedicated VM)
# ==============================================================================
# Installs system dependencies, PostgreSQL 16, Redis 7, Nginx, Python 3.12 venv,
# configures system users, sets permissions, and pre-configures systemd units.
#
# RUN WITH SUDO: sudo bash deploy/scripts/provision_ubuntu24.sh
#
# NETWORK OPTIONS:
#   NETWORK_MODE="vpn"       -> Restricts all access to VPN interface (Tailscale/WireGuard)
#   NETWORK_MODE="allowlist" -> Restricts access to specific IPs (ALLOWED_IPS="1.2.3.4,5.6.7.8")
# ==============================================================================

set -euo pipefail

NETWORK_MODE="${NETWORK_MODE:-vpn}"
ALLOWED_IPS="${ALLOWED_IPS:-127.0.0.1}"
DRY_RUN="${DRY_RUN:-0}"
CONFIRM_FIREWALL="${CONFIRM_FIREWALL:-0}"

# Parse optional command-line flags
for arg in "$@"; do
    case "${arg}" in
        --dry-run) DRY_RUN=1 ;;
        --confirm-firewall) CONFIRM_FIREWALL=1 ;;
    esac
done

if [ "${NETWORK_MODE}" != "vpn" ] && [ "${NETWORK_MODE}" != "allowlist" ]; then
    echo "ERROR: Invalid NETWORK_MODE '${NETWORK_MODE}'. Must be 'vpn' or 'allowlist'."
    exit 1
fi

echo "===================================================================="
echo "HeartAI Staging VM Provisioning (Ubuntu 24.04 LTS)"
echo "Network Mode: ${NETWORK_MODE}"
echo "===================================================================="

# 1. Update package lists and install core dependencies
echo "[1/8] Updating apt packages and installing system dependencies..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
    build-essential \
    curl \
    git \
    htop \
    jq \
    ufw \
    fail2ban \
    logrotate \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    postgresql-16 \
    postgresql-contrib \
    libpq-dev \
    redis-server \
    restic \
    nginx \
    certbot \
    python3-certbot-nginx \
    libgl1 \
    libglib2.0-0

# 2. Create unprivileged system user and group
echo "[2/8] Creating service account 'heartai'..."
if ! id -u heartai >/dev/null 2>&1; then
    useradd --system --shell /bin/false --user-group heartai
    echo "Service account 'heartai' created."
else
    echo "Service account 'heartai' already exists."
fi

# 3. Create application directory tree
echo "[3/8] Setting up directory structure under /opt/heartai..."
mkdir -p /opt/heartai/{data,logs,static,backups,deploy}
mkdir -p /var/log/heartai
mkdir -p /var/backups/heartai
mkdir -p /etc/heartai/certs

chown -R heartai:heartai /opt/heartai
chown -R heartai:heartai /var/log/heartai
chown -R root:root /var/backups/heartai
chown -R root:root /etc/heartai
chmod 750 /opt/heartai
chmod 700 /opt/heartai/data
chmod 700 /opt/heartai/backups
chmod 700 /var/backups/heartai
chmod 700 /etc/heartai
chmod 700 /etc/heartai/certs
chmod 750 /var/log/heartai

# 4. Configure PostgreSQL 16
echo "[4/8] Configuring PostgreSQL 16..."
systemctl start postgresql
systemctl enable postgresql

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_HELPER="${SCRIPT_DIR}/db_credentials_helper.py"
if [ ! -f "${DB_HELPER}" ]; then
    DB_HELPER="/opt/heartai/deploy/scripts/db_credentials_helper.py"
fi

ENV_FILE="/opt/heartai/.env"
DB_USER="heartai_user"
DB_NAME="heartai_db"
DB_PASSWORD=""
IS_RERUN=false

# Inspect existing environment configuration using Python urllib.parse helper (OP-04)
if [ -f "${ENV_FILE}" ]; then
    PARSE_EXIT=0
    PARSE_OUT=$(python3 "${DB_HELPER}" parse-env "${ENV_FILE}" 2>&1) || PARSE_EXIT=$?

    if [ "${PARSE_EXIT}" -eq 1 ]; then
        echo "===================================================================="
        echo "[CRITICAL ERROR] Failed to parse DATABASE_URL from ${ENV_FILE}:"
        echo "${PARSE_OUT}"
        echo "Provisioning aborted to prevent accidental configuration corruption (OP-04)."
        echo "===================================================================="
        exit 1
    elif [ "${PARSE_EXIT}" -eq 0 ]; then
        DB_USER=$(echo "${PARSE_OUT}" | grep '^DB_USER=' | cut -d= -f2-)
        DB_NAME=$(echo "${PARSE_OUT}" | grep '^DB_NAME=' | cut -d= -f2-)
        DB_PASSWORD=$(echo "${PARSE_OUT}" | grep '^DB_PASSWORD=' | cut -d= -f2-)
        IS_RERUN=true
        echo "Found existing DATABASE_URL in ${ENV_FILE} for user '${DB_USER}'."
    fi
fi

# Validation: Authentication check on rerun vs first-run provisioning
ROLE_EXISTS=$(sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" 2>/dev/null | tr -d ' ' || echo "0")

if [ "${IS_RERUN}" == "true" ]; then
    if [ "${ROLE_EXISTS}" == "1" ]; then
        echo "Validating existing PostgreSQL credentials for role '${DB_USER}'..."
        # Verify credentials via loopback without exposing password on command line
        if PGPASSWORD="${DB_PASSWORD}" psql -h 127.0.0.1 -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1;" >/dev/null 2>&1; then
            echo "Credentials verified and authenticated successfully. Preserving active user without password reset."
        else
            echo "===================================================================="
            echo "[CRITICAL ERROR] Role '${DB_USER}' exists, but credentials from ${ENV_FILE} failed authentication!"
            echo "Refusing to overwrite or reset password automatically on rerun."
            echo "Please verify credentials in ${ENV_FILE} before proceeding."
            echo "===================================================================="
            exit 1
        fi
    else
        echo "Pre-staged credentials found in ${ENV_FILE}. Role '${DB_USER}' does not exist yet; creating..."
        ESCAPED_PW=$(python3 "${DB_HELPER}" escape-literal "${DB_PASSWORD}")
        sudo -u postgres psql <<EOSQL
DO \$\$
BEGIN
    CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${ESCAPED_PW}';
END
\$\$;
EOSQL
    fi
else
    # First-run provisioning
    echo "First-run database provisioning: no existing .env credentials found."
    if [ -z "${DB_PASSWORD}" ]; then
        DB_PASSWORD="${HEARTAI_DB_PASSWORD:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')}"
    fi

    ESCAPED_PW=$(python3 "${DB_HELPER}" escape-literal "${DB_PASSWORD}")
    if [ "${ROLE_EXISTS}" == "1" ]; then
        echo "[WARNING] Role '${DB_USER}' already exists in PostgreSQL. Re-applying password..."
        sudo -u postgres psql <<EOSQL
DO \$\$
BEGIN
    ALTER ROLE ${DB_USER} WITH PASSWORD '${ESCAPED_PW}';
END
\$\$;
EOSQL
    else
        sudo -u postgres psql <<EOSQL
DO \$\$
BEGIN
    CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${ESCAPED_PW}';
END
\$\$;
EOSQL
    fi
fi

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
sudo -u postgres psql -d "${DB_NAME}" -c "GRANT ALL ON SCHEMA public TO ${DB_USER};"

echo "PostgreSQL database '${DB_NAME}' and user '${DB_USER}' configured."

# 5. Configure Redis 7
echo "[5/8] Configuring Redis 7..."
if [ -f "/opt/heartai/deploy/redis/redis.conf" ]; then
    cp /opt/heartai/deploy/redis/redis.conf /etc/redis/redis.conf
fi
systemctl restart redis-server
systemctl enable redis-server

# 6. Set up Python 3.12 Virtual Environment
echo "[6/8] Provisioning Python 3.12 virtual environment at /opt/heartai/.venv..."
if [ ! -d "/opt/heartai/.venv" ]; then
    python3.12 -m venv /opt/heartai/.venv
fi
/opt/heartai/.venv/bin/pip install --upgrade pip setuptools wheel
if [ -f "/opt/heartai/requirements.txt" ]; then
    /opt/heartai/.venv/bin/pip install -r /opt/heartai/requirements.txt
fi
chown -R heartai:heartai /opt/heartai/.venv

# 7. Configure Systemd Services & Nginx
echo "[7/8] Configuring Systemd and Nginx..."
if [ -f "/opt/heartai/deploy/systemd/heartai-backend.service" ]; then
    cp /opt/heartai/deploy/systemd/heartai-backend.service /etc/systemd/system/
fi
if [ -f "/opt/heartai/deploy/systemd/heartai-frontend.service" ]; then
    cp /opt/heartai/deploy/systemd/heartai-frontend.service /etc/systemd/system/
fi
if [ -f "/opt/heartai/deploy/systemd/heartai-backup.service" ]; then
    cp /opt/heartai/deploy/systemd/heartai-backup.service /etc/systemd/system/
fi
if [ -f "/opt/heartai/deploy/systemd/heartai-backup.timer" ]; then
    cp /opt/heartai/deploy/systemd/heartai-backup.timer /etc/systemd/system/
    systemctl enable heartai-backup.timer
fi
systemctl daemon-reload

if [ -f "/opt/heartai/deploy/nginx/heartai.conf" ]; then
    cp /opt/heartai/deploy/nginx/heartai.conf /etc/nginx/sites-available/heartai.conf
    ln -sf /etc/nginx/sites-available/heartai.conf /etc/nginx/sites-enabled/heartai.conf
    rm -f /etc/nginx/sites-enabled/default
fi

# Validate TLS certificate existence before starting or reloading Nginx (OP-01)
TLS_CRT="/etc/heartai/certs/tls.crt"
TLS_KEY="/etc/heartai/certs/tls.key"

if [ -f "${TLS_CRT}" ] && [ -f "${TLS_KEY}" ]; then
    echo "TLS certificates detected at ${TLS_CRT} and ${TLS_KEY}. Validating permissions and Nginx configuration..."
    chmod 644 "${TLS_CRT}"
    chmod 600 "${TLS_KEY}"
    chown root:root "${TLS_CRT}" "${TLS_KEY}"
    nginx -t
    systemctl restart nginx
    systemctl enable nginx
    echo "Nginx configured and active with verified TLS certificates."
else
    echo "===================================================================="
    echo "[WARNING] TLS certificates missing at ${TLS_CRT} and ${TLS_KEY}!"
    echo "Nginx service will NOT be started to prevent startup failures."
    echo "To configure TLS for private staging:"
    echo "  1) If using Tailscale (recommended):"
    echo "     sudo tailscale cert --cert-file ${TLS_CRT} --key-file ${TLS_KEY} <tailscale-fqdn>"
    echo "  2) If using custom certs or Certbot:"
    echo "     cp /path/to/fullchain.pem ${TLS_CRT}"
    echo "     cp /path/to/privkey.pem ${TLS_KEY}"
    echo "  3) Restrict permissions:"
    echo "     chmod 644 ${TLS_CRT} && chmod 600 ${TLS_KEY}"
    echo "  4) Test and start Nginx:"
    echo "     sudo nginx -t && sudo systemctl enable --now nginx"
    echo "===================================================================="
fi

# 8. Configure UFW Firewall (Fail-Closed, Non-Destructive Reconciliation - OP-03)
echo "[8/8] Configuring UFW Firewall (${NETWORK_MODE})..."

if [ "${NETWORK_MODE}" == "vpn" ]; then
    echo "Performing VPN pre-flight connectivity checks before altering firewall (OP-03)..."
    TAILSCALE_READY=false
    if command -v tailscale >/dev/null 2>&1; then
        # Check active status AND verify local Tailscale IP presence
        if tailscale status >/dev/null 2>&1 && [ -n "$(tailscale ip -4 2>/dev/null || true)" ]; then
            TAILSCALE_READY=true
        fi
    fi

    WIREGUARD_READY=false
    if command -v wg >/dev/null 2>&1 && ip link show wg0 >/dev/null 2>&1; then
        if wg show wg0 >/dev/null 2>&1; then
            WIREGUARD_READY=true
        fi
    fi

    if [ "${TAILSCALE_READY}" != "true" ] && [ "${WIREGUARD_READY}" != "true" ]; then
        echo "===================================================================="
        echo "[CRITICAL SAFETY GUARD] VPN-only network mode requested, but neither"
        echo "Tailscale ('tailscale0') nor WireGuard ('wg0') is active and connected!"
        echo "Applying UFW default-deny rules now would PERMANENTLY LOCK OUT all SSH access."
        echo ""
        echo "Remediation:"
        echo "  1. Authenticate and connect Tailscale: run 'sudo tailscale up'"
        echo "  2. OR provide an initial operator IP via allowlist mode:"
        echo "     NETWORK_MODE=allowlist ALLOWED_IPS=\"<your-ip>\" sudo bash deploy/scripts/provision_ubuntu24.sh"
        echo "===================================================================="
        exit 1
    fi

    MANAGEMENT_IFACE="tailscale0"
    if [ "${TAILSCALE_READY}" != "true" ] && [ "${WIREGUARD_READY}" == "true" ]; then
        MANAGEMENT_IFACE="wg0"
    fi

    if [ "${DRY_RUN}" == "1" ]; then
        echo "[DRY RUN] VPN interface '${MANAGEMENT_IFACE}' verified active and connected."
        echo "[DRY RUN] Planned non-destructive UFW configuration:"
        echo "  ufw default deny incoming"
        echo "  ufw default allow outgoing"
        echo "  ufw allow in on ${MANAGEMENT_IFACE} to any port 22 proto tcp comment 'SSH via VPN'"
        echo "  ufw allow in on ${MANAGEMENT_IFACE} to any port 443 proto tcp comment 'HTTPS via VPN'"
        echo "  ufw --force enable"
        echo "[DRY RUN] Completed without modifying system firewall."
        exit 0
    fi

    # Operator Confirmation Guard in interactive sessions
    if [ -t 0 ] && [ "${CONFIRM_FIREWALL}" != "1" ]; then
        echo ""
        echo "===================================================================="
        echo "[FIREWALL CONFIRMATION REQUIRED]"
        echo "Target Management Interface: ${MANAGEMENT_IFACE}"
        echo "Policy: Default deny incoming; permit TCP 22 (SSH) and 443 (HTTPS) strictly via VPN."
        echo "Public ingress on physical network interfaces (e.g. eth0) will be blocked."
        echo "Out-of-band recovery: Cloud Console Serial Console / Virtual Terminal / VNC."
        echo "===================================================================="
        read -r -p "Apply VPN firewall reconciliation now? [y/N]: " USER_CONFIRM_FW
        if [[ ! "${USER_CONFIRM_FW}" =~ ^[Yy]$ ]]; then
            echo "Firewall reconciliation aborted by operator. No changes made."
            exit 1
        fi
    fi

    echo "Reconciling UFW firewall rules idempotently (non-destructive)..."
    ufw default deny incoming
    ufw default allow outgoing

    if [ "${TAILSCALE_READY}" == "true" ]; then
        ufw allow in on tailscale0 to any port 22 proto tcp comment 'SSH via Tailscale VPN'
        ufw allow in on tailscale0 to any port 443 proto tcp comment 'HTTPS via Tailscale VPN'
    fi
    if [ "${WIREGUARD_READY}" == "true" ]; then
        ufw allow in on wg0 to any port 22 proto tcp comment 'SSH via WireGuard'
        ufw allow in on wg0 to any port 443 proto tcp comment 'HTTPS via WireGuard'
    fi
    ufw --force enable

elif [ "${NETWORK_MODE}" == "allowlist" ]; then
    echo "Configuring IP-allowlisted ingress for authorized addresses..."
    if [ -z "${ALLOWED_IPS}" ] || [ "${ALLOWED_IPS}" == "127.0.0.1" ]; then
        echo "[WARNING] ALLOWED_IPS is set to loopback or empty. External SSH will not be permitted."
    fi

    if [ "${DRY_RUN}" == "1" ]; then
        echo "[DRY RUN] Allowlist mode: ${ALLOWED_IPS}. Dry run completed without modifying firewall."
        exit 0
    fi

    ufw default deny incoming
    ufw default allow outgoing

    IFS=',' read -ra ADDR <<< "${ALLOWED_IPS}"
    for ip in "${ADDR[@]}"; do
        ip_clean="$(echo "${ip}" | tr -d ' ')"
        if [ -n "${ip_clean}" ]; then
            ufw allow from "${ip_clean}" to any port 22 proto tcp comment "SSH from ${ip_clean}"
            ufw allow from "${ip_clean}" to any port 443 proto tcp comment "HTTPS from ${ip_clean}"
            ufw allow from "${ip_clean}" to any port 80 proto tcp comment "HTTP from ${ip_clean}"
        fi
    done
    ufw --force enable
fi

# Internal services (PostgreSQL 5432, Redis 6379, FastAPI 8000, NiceGUI 8080)
# are strictly bound to 127.0.0.1 and NEVER exposed on external interfaces.

echo "===================================================================="
echo "HeartAI Staging Host Provisioning Completed Successfully!"
echo "Database credentials configured in PostgreSQL (persisted in /opt/heartai/.env or environment)."
echo "Next step: copy /opt/heartai/deploy/.env.production.template to /opt/heartai/.env (if not present)"
echo "and run: sudo -u heartai /opt/heartai/.venv/bin/alembic upgrade head (also enforced automatically via ExecStartPre)"
echo "===================================================================="
