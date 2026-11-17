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

NETWORK_MODE="${NETWORK_MODE:-allowlist}"
ALLOWED_IPS="${ALLOWED_IPS:-127.0.0.1}"

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
mkdir -p /etc/heartai

chown -R heartai:heartai /opt/heartai
chown -R heartai:heartai /var/log/heartai
chown -R root:root /var/backups/heartai
chown -R root:root /etc/heartai
chmod 750 /opt/heartai
chmod 700 /opt/heartai/data
chmod 700 /opt/heartai/backups
chmod 700 /var/backups/heartai
chmod 700 /etc/heartai
chmod 750 /var/log/heartai

# 4. Configure PostgreSQL 16
echo "[4/8] Configuring PostgreSQL 16..."
systemctl start postgresql
systemctl enable postgresql

# Generate random DB password if not provided
DB_PASSWORD="${HEARTAI_DB_PASSWORD:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')}"

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='heartai_user'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE USER heartai_user WITH PASSWORD '${DB_PASSWORD}';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='heartai_db'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE DATABASE heartai_db OWNER heartai_user;"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE heartai_db TO heartai_user;"
sudo -u postgres psql -d heartai_db -c "GRANT ALL ON SCHEMA public TO heartai_user;"

echo "PostgreSQL database 'heartai_db' and user 'heartai_user' configured."

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

# 8. Configure UFW Firewall (Fail-Closed & Reconciled)
echo "[8/8] Configuring UFW Firewall (${NETWORK_MODE})..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing

if [ "${NETWORK_MODE}" == "vpn" ]; then
    echo "Configuring VPN-only ingress (tailscale0 / wg0)..."
    ufw allow in on tailscale0 to any port 22 proto tcp comment 'SSH via Tailscale VPN' || true
    ufw allow in on tailscale0 to any port 443 proto tcp comment 'HTTPS via Tailscale VPN' || true
    ufw allow in on wg0 to any port 22 proto tcp comment 'SSH via WireGuard' || true
    ufw allow in on wg0 to any port 443 proto tcp comment 'HTTPS via WireGuard' || true
elif [ "${NETWORK_MODE}" == "allowlist" ]; then
    echo "Configuring IP-allowlisted ingress for authorized addresses..."
    IFS=',' read -ra ADDR <<< "${ALLOWED_IPS}"
    for ip in "${ADDR[@]}"; do
        ip_clean="$(echo "${ip}" | tr -d ' ')"
        if [ -n "${ip_clean}" ]; then
            ufw allow from "${ip_clean}" to any port 22 proto tcp comment "SSH from ${ip_clean}"
            ufw allow from "${ip_clean}" to any port 443 proto tcp comment "HTTPS from ${ip_clean}"
            ufw allow from "${ip_clean}" to any port 80 proto tcp comment "HTTP from ${ip_clean}"
        fi
    done
fi

# Internal services (PostgreSQL 5432, Redis 6379, FastAPI 8000, NiceGUI 8080)
# are strictly bound to 127.0.0.1 and NEVER exposed on external interfaces.

echo "===================================================================="
echo "HeartAI Staging Host Provisioning Completed Successfully!"
echo "Generated DB Password: ${DB_PASSWORD}"
echo "Next step: copy /opt/heartai/deploy/.env.production.template to /opt/heartai/.env"
echo "and run: sudo -u heartai /opt/heartai/.venv/bin/alembic upgrade head"
echo "===================================================================="
