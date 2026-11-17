# HeartAI Production Deployment Guide

**Application**: HeartAI — Cardiovascular Research & Educational Platform  
**Target Environment**: Linux (Ubuntu 24.04 LTS / Debian 12)  
**Python Runtime**: Python 3.12+  
**Process Manager**: Systemd (`heartai-backend.service`, `heartai-frontend.service`) / Gunicorn + Uvicorn Workers  
**Web Server / Proxy**: Nginx with TLS 1.3  
**Database**: PostgreSQL 16 (Production) with Alembic Migrations  
**Cache / Rate Limit Storage**: Redis 7+ (for distributed multi-worker setups)  

---

## 1. Production Architecture Overview

```
                      Evaluators / Clients (Tailscale VPN)
                                       │
                                       ▼ (HTTPS :443 / WSS :443)
                           ┌───────────────────────┐
                           │         Nginx         │  TLS Termination, Static Delivery,
                           │     Reverse Proxy     │  Header Hardening, Rate Limiting
                           └───────────┬───────────┘
                                       │
             ┌─────────────────────────┴─────────────────────────┐
             │ Path: /                                           │ Path: ^/(api|predict|health|docs)
             ▼                                                   ▼
┌─────────────────────────┐                         ┌─────────────────────────┐
│     NiceGUI Frontend    │                         │   Gunicorn Master       │
│     Motion UI Service   │                         │  ┌───────────────────┐  │
│  (127.0.0.1:8080)       │                         │  │ Uvicorn Workers   │  │
│  Interactive WebSockets │                         │  │ (127.0.0.1:8000)  │  │
└─────────────────────────┘                         └─────────┬─────────┬─────┘
                                                              │         │
                                                              ▼         ▼
                                                     ┌──────────────┐ ┌──────────────┐
                                                     │  PostgreSQL  │ │   Redis 7+   │
                                                     │  (Port 5432) │ │  (Port 6379) │
                                                     └──────────────┘ └──────────────┘
```

---

## 2. Server Prerequisites & System Provisioning

Execute the following commands on a clean Ubuntu 22.04/24.04 LTS server:

```bash
# 1. Update OS packages
sudo apt update && sudo apt upgrade -y

# 2. Install base build tools, Python 3.12, PostgreSQL client, and Nginx
sudo apt install -y python3.12 python3.12-venv python3.12-dev \
    build-essential libpq-dev git nginx curl redis-server

# 3. Create dedicated system user for running HeartAI
sudo useradd -m -s /bin/bash heartai
sudo usermod -aG systemd-journal heartai

# 4. Create application directories
sudo mkdir -p /opt/heartai /var/log/heartai /var/run/heartai
sudo chown -R heartai:heartai /opt/heartai /var/log/heartai /var/run/heartai
```

---

## 3. Application Deployment & Virtual Environment

Log in as the `heartai` user and clone the repository:

```bash
sudo -u heartai -i
cd /opt/heartai

# Clone repository
git clone https://github.com/your-org/heart-health-moniter-system.git .
git checkout main

# Create Python 3.12 virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install production dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install gunicorn uvicorn[standard] psycopg2-binary redis
```

---

## 4. Environment & Secrets Configuration

Create `/opt/heartai/.env` with strict 600 permissions:

```bash
# Generate high-entropy secret key:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Configure `/opt/heartai/.env`:

```ini
APP_ENV=production
APP_DEBUG=false
APP_HOST=127.0.0.1
APP_PORT=8000
FRONTEND_HOST=127.0.0.1
FRONTEND_PORT=8080
BACKEND_API_URL=https://heartai-staging.your-tailnet.ts.net

# High-entropy cryptographically secure secret (minimum 32 characters)
SECRET_KEY=paste_generated_32_plus_char_secret_here
TELEMETRY_HMAC_KEY=paste_generated_32_plus_char_hmac_key_here

# Database Configuration (PostgreSQL)
DATABASE_URL=postgresql://heartai_user:YourStrongPasswordHere@localhost:5432/heartai_db

# Distributed Rate Limiting Storage
REDIS_URL=redis://localhost:6379/0

# CORS Whitelist (Production Domains)
CORS_ORIGINS=["https://heartai-staging.your-tailnet.ts.net"]

# Rate Limiting Tiers
RATE_LIMIT_DEFAULT=60/minute
RATE_LIMIT_AUTH=10/minute
RATE_LIMIT_AI_CHAT=20/minute
RATE_LIMIT_AI_SYMPTOMS=15/minute
RATE_LIMIT_AI_PERSONALIZED=10/minute

# Model Governance
MODEL_PATH=models/best_model.joblib
PREPROCESSOR_PATH=models/preprocessing_pipeline.joblib
METADATA_PATH=models/model_metadata.json
OPERATING_THRESHOLD=0.09

# Generative AI (Google Gemini API - Optional)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash
GEMINI_TIMEOUT_SECONDS=15.0
GEMINI_MAX_OUTPUT_TOKENS=1024
GEMINI_TEMPERATURE=0.2

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=/var/log/heartai/heartai.log
```

Protect the configuration:
```bash
chmod 600 /opt/heartai/.env
```

---

## 5. PostgreSQL Database Provisioning

On the PostgreSQL server:

```sql
-- Create database user and database
CREATE USER heartai_user WITH PASSWORD 'YourStrongPasswordHere';
CREATE DATABASE heartai_db OWNER heartai_user;
GRANT ALL PRIVILEGES ON DATABASE heartai_db TO heartai_user;

-- Connect to database and configure schema permissions
\c heartai_db
GRANT ALL ON SCHEMA public TO heartai_user;
```

Initialize database schema using declarative Alembic migrations:
```bash
cd /opt/heartai
source .venv/bin/activate
alembic upgrade head
```

---

## 6. Gunicorn Process Supervisor Configuration

Inspect repository configuration file `deploy/gunicorn.conf.py`:

```python
"""Gunicorn production configuration for HeartAI."""

import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
backlog = 2048
default_workers = min(multiprocessing.cpu_count() * 2 + 1, 8)
workers = int(os.environ.get("GUNICORN_WORKERS", default_workers))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 60
keepalive = 5
graceful_timeout = 30
max_requests = 5000
max_requests_jitter = 500

# Logging
accesslog = os.environ.get("GUNICORN_ACCESS_LOG", "/var/log/heartai/access.log")
errorlog = os.environ.get("GUNICORN_ERROR_LOG", "/var/log/heartai/error.log")
loglevel = os.environ.get("LOG_LEVEL", "info").lower()

# Security & Isolation
proc_name = "heartai-gunicorn"
daemon = False
```

---

## 7. Systemd Service Definitions

HeartAI operates as two decoupled systemd services:
1. `heartai-backend.service`: FastAPI ASGI application managed by Gunicorn and Uvicorn workers.
2. `heartai-frontend.service`: NiceGUI interactive UI and WebSocket motion service.

### 7.1 Backend Service: `/etc/systemd/system/heartai-backend.service`

```ini
[Unit]
Description=HeartAI FastAPI Backend Service (Gunicorn + Uvicorn)
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=notify
User=heartai
Group=heartai
WorkingDirectory=/opt/heartai
EnvironmentFile=/opt/heartai/.env
ExecStart=/opt/heartai/.venv/bin/gunicorn -c deploy/gunicorn.conf.py main:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=30
Restart=always
RestartSec=5s
LimitNOFILE=65535

# Security Hardening Directives
ProtectSystem=full
ProtectHome=true
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### 7.2 Frontend Service: `/etc/systemd/system/heartai-frontend.service`

```ini
[Unit]
Description=HeartAI NiceGUI Frontend & Interactive Motion Service
After=network.target heartai-backend.service
Wants=heartai-backend.service

[Service]
Type=simple
User=heartai
Group=heartai
WorkingDirectory=/opt/heartai
EnvironmentFile=/opt/heartai/.env
ExecStart=/opt/heartai/.venv/bin/python motion_demo.py
Restart=always
RestartSec=5s
LimitNOFILE=65535

# Security Hardening Directives
ProtectSystem=full
ProtectHome=true
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### 7.3 Enable and Start Application Services

```bash
sudo cp deploy/systemd/heartai-backend.service /etc/systemd/system/
sudo cp deploy/systemd/heartai-frontend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now heartai-backend.service heartai-frontend.service
sudo systemctl status heartai-backend.service heartai-frontend.service
```

---

## 8. Nginx Reverse Proxy Configuration

Install the verified configuration from `deploy/nginx/heartai.conf`:

```nginx
# Map for WebSocket connection upgrade
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 80;
    listen [::]:80;
    server_name heartai-staging.your-tailnet.ts.net;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name heartai-staging.your-tailnet.ts.net;

    # SSL / TLS 1.3 Configuration (Tailscale MagicDNS or ACME DNS-01)
    ssl_certificate /var/lib/tailscale/certs/heartai-staging.crt;
    ssl_certificate_key /var/lib/tailscale/certs/heartai-staging.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # HTTP Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' wss: https:;" always;

    # Client limits
    client_max_body_size 10M;

    # Static Assets Direct Delivery (Bypasses Python runtime)
    location /static/ {
        alias /opt/heartai/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
        access_log off;
    }

    # FastAPI Backend Routes (REST API, Health, ML Inference, OpenAPI docs)
    location ~ ^/(api|predict|health|model-info|docs|redoc|openapi.json) {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_read_timeout 60s;
        proxy_buffering on;
    }

    # NiceGUI Frontend & Interactive WebSockets (Root application)
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
```

Enable site and reload Nginx:
```bash
sudo cp deploy/nginx/heartai.conf /etc/nginx/sites-available/heartai.conf
sudo ln -sf /etc/nginx/sites-available/heartai.conf /etc/nginx/sites-enabled/heartai.conf
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

---

## 9. Verification & Health Probes

Verify the active deployment:

```bash
# 1. Check local health endpoint
curl -i http://127.0.0.1:8000/health

# Expected response: HTTP 200 OK
# {
#   "status": "healthy",
#   "database": {"connected": true},
#   "model": {
#     "loaded": true,
#     "sha256_verified": true,
#     "preprocessor_sha256_verified": true,
#     "operating_threshold": 0.09
#   }
# }

# 2. Check model info endpoint
curl -i http://127.0.0.1:8000/model-info

# 3. Service restart and status check
sudo systemctl restart heartai-backend.service
sudo systemctl restart heartai-frontend.service
sudo systemctl status heartai-backend.service heartai-frontend.service
```

---

## 10. Client-Side Encrypted Backup & Disaster Recovery (Restic)

HeartAI implements a client-side encrypted backup architecture using Restic and PostgreSQL custom dumps.

### 10.1 Key Architecture & Verified Cryptographic Algorithms
1. **Target Restic Version**: `restic 0.16.4` (Ubuntu 24.04 LTS Noble Numbat package).
2. **Verified Cryptographic Suite**:
   - **Data Cipher**: **AES-256 in Counter Mode (AES-256-CTR)** (RFC 3686).
   - **Message Authentication**: **Poly1305-AES MAC** (RFC 8439).
   - **Key Derivation Function**: **scrypt** (`N=32768, r=8, p=5`) for master password hashing, and SHA-256 for key derivation.
   - **Chunk Identification**: **SHA-256** hash over compressed ciphertext blobs.
   - *Note on Cryptographic Corrections: Restic does NOT use AES-256-GCM. All references have been reconciled to the authoritative AES-256-CTR + Poly1305 AEAD construction.*
3. **Streaming Database Dumps**: The streaming pipeline does not intentionally write plaintext database dump files to persistent storage. The backup script streams `pg_dump -Fc` directly from memory into `restic backup --stdin`.
4. **Key Management & Root Compromise Model**: The encryption key is stored at `/etc/heartai/backup_key` (`chmod 400`, owned by `root:root`). Root compromise of the VM may expose the locally stored backup key. Off-host key escrow (e.g. in an offline physical safe or enterprise secrets manager) supports disaster recovery in the event of host destruction, but does not protect against live root compromise.
5. **Difference from Storage Provider Encryption**: Cloud provider encryption-at-rest (e.g. AWS S3 SSE-S3) only protects physical drives; it does not protect against compromised cloud credentials or API leaks. Client-side encryption ensures the storage provider receives only encrypted ciphertext chunks without possession of the decryption key.
6. **Automated Scheduling**: Backups are orchestrated via systemd timer (`heartai-backup.timer`) triggering `heartai-backup.service` hourly.
7. **Mutual Exclusion**: Script execution is protected by `flock -n /run/lock/heartai-backup.lock` to prevent overlapping runs.

### 10.2 Enabling Automated Hourly Backups
```bash
# 1. Install Restic
sudo apt install -y restic

# 2. Initialize encryption key file
sudo mkdir -p /etc/heartai
python3 -c 'import secrets; print(secrets.token_urlsafe(32))' | sudo tee /etc/heartai/backup_key >/dev/null
sudo chmod 400 /etc/heartai/backup_key
sudo chown root:root /etc/heartai/backup_key

# 3. Install and enable systemd units
sudo cp deploy/systemd/heartai-backup.service /etc/systemd/system/
sudo cp deploy/systemd/heartai-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now heartai-backup.timer

# 4. Verify timer status
sudo systemctl list-timers heartai-backup.timer
```

### 10.3 Manual Backup & Restoration Commands
```bash
# Execute manual backup:
sudo /opt/heartai/deploy/scripts/backup_staging.sh

# Verify repository snapshots:
sudo RESTIC_PASSWORD_FILE=/etc/heartai/backup_key restic -r /var/backups/heartai snapshots

# Execute safe restore drill (into staging scratch DB first, verified, then promoted):
sudo /opt/heartai/deploy/scripts/restore_staging.sh latest --confirm
```

### 10.4 Immutable Retention (WORM) vs Pruning Incompatibility
- **The Incompatibility**: Restic's `forget --prune` command repacks and deletes unreferenced pack files via `s3:DeleteObject`. If AWS S3 Object Lock (WORM) is enabled on the repository bucket, S3 rejects delete operations with `403 ObjectLocked`, causing prune jobs to fail.
- **Reconciled Staging Strategy**: For staging, use **S3 Bucket Versioning with a 14-day noncurrent version expiration lifecycle rule** (without Object Lock) so that Restic can prune snapshots while versioning protects against deletion or ransomware.
- **Compliance WORM Archival Mode**: If compliance mandates WORM Object Lock, Restic must be run in append-only mode and `--prune` must be disabled on that bucket. Deletion of expired pack files is deferred entirely to S3 Lifecycle expiration rules matching the legal hold duration.

