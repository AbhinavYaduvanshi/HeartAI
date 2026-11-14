# HeartAI Production Deployment Guide

**Application**: HeartAI — Cardiovascular Clinical Intelligence Platform  
**Target Environment**: Linux (Ubuntu 22.04 LTS / 24.04 LTS or Debian 12)  
**Python Runtime**: Python 3.12+  
**Process Manager**: Systemd / Gunicorn + Uvicorn Workers  
**Web Server / Proxy**: Nginx with TLS 1.3  
**Database**: PostgreSQL 15+ (Production) / SQLite (Local Single-Node Only)  
**Cache / Rate Limit Storage**: Redis 7+ (for distributed multi-worker setups)  

---

## 1. Production Architecture Overview

```
                      Internet / Clients
                             │
                             ▼ (HTTPS :443 / WSS :443)
                 ┌───────────────────────┐
                 │         Nginx         │  TLS Termination, Static Cache,
                 │     Reverse Proxy     │  Header Hardening, Rate Limiting
                 └───────────┬───────────┘
                             │
                             ▼ (Unix Socket or http://127.0.0.1:8000)
                 ┌───────────────────────┐
                 │   Gunicorn Master     │  Process Supervisor
                 │  ┌─────────────────┐  │
                 │  │ Uvicorn Worker 1│  │  ASGI Async Runtime
                 │  │ Uvicorn Worker 2│  │  (Workers = 2 * CPUs + 1)
                 │  │ Uvicorn Worker N│  │
                 │  └─────────────────┘  │
                 └──────┬──────────┬─────┘
                        │          │
                        ▼          ▼
           ┌────────────────┐  ┌────────────────┐
           │   PostgreSQL   │  │  Redis 7+      │
           │   Database     │  │  Rate Limiter  │
           │   (Port 5432)  │  │  (Port 6379)   │
           └────────────────┘  └────────────────┘
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

# High-entropy cryptographically secure secret (minimum 32 characters)
SECRET_KEY=paste_generated_32_plus_char_secret_here

# Database Configuration (PostgreSQL)
DATABASE_URL=postgresql://heartai_user:YourStrongPasswordHere@localhost:5432/heartai_db

# Distributed Rate Limiting Storage
REDIS_URL=redis://localhost:6379/0

# CORS Whitelist (Production Domains)
CORS_ORIGINS=["https://heartai.yourdomain.org","https://www.heartai.yourdomain.org"]

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

# Generative AI (Google Gemini API)
GEMINI_API_KEY=your_production_google_gemini_api_key
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

Initialize database tables:
```bash
cd /opt/heartai
source .venv/bin/activate
python3 -c "from app.db.session import init_db; init_db()"
```

---

## 6. Gunicorn Process Supervisor Configuration

Create `/opt/heartai/gunicorn.conf.py`:

```python
"""Gunicorn production configuration for HeartAI."""

import multiprocessing
import os

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 60
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "/var/log/heartai/access.log"
errorlog = "/var/log/heartai/error.log"
loglevel = "info"

# Security & Isolation
proc_name = "heartai_api"
user = "heartai"
group = "heartai"
```

---

## 7. Systemd Service Definition

Create `/etc/systemd/system/heartai.service`:

```ini
[Unit]
Description=HeartAI Clinical Intelligence Platform Service
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=simple
User=heartai
Group=heartai
WorkingDirectory=/opt/heartai
EnvironmentFile=/opt/heartai/.env
ExecStart=/opt/heartai/.venv/bin/gunicorn -c /opt/heartai/gunicorn.conf.py main:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=15
Restart=on-failure
RestartSec=5s

# Security Sandboxing Directives
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/opt/heartai /var/log/heartai /var/run/heartai

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable heartai.service
sudo systemctl start heartai.service
sudo systemctl status heartai.service
```

---

## 8. Nginx Reverse Proxy Configuration

Create `/etc/nginx/sites-available/heartai.conf`:

```nginx
# Rate limiting zone
limit_req_zone $binary_remote_addr zone=heartai_limit:10m rate=30r/s;

server {
    listen 80;
    server_name heartai.yourdomain.org;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name heartai.yourdomain.org;

    # SSL / TLS 1.3 Configuration
    ssl_certificate /etc/letsencrypt/live/heartai.yourdomain.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/heartai.yourdomain.org/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5:!3DES;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # HTTP Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self' wss: https:;" always;

    # Client limits
    client_max_body_size 5M;

    # Static Assets Cache
    location /static/ {
        alias /opt/heartai/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # API and Dynamic Application Proxy
    location / {
        limit_req zone=heartai_limit burst=50 nodelay;

        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        # WebSocket support for NiceGUI motion engine
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
    }
}
```

Enable site and reload Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/heartai.conf /etc/nginx/sites-enabled/
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

# 3. Test zero-downtime reload
sudo systemctl reload heartai.service
```
