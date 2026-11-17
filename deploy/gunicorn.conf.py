"""HeartAI Gunicorn Production Server Configuration.

Supervises asynchronous Uvicorn workers for FastAPI backend serving.
"""

import multiprocessing
import os

# Server socket & reverse proxy headers (REL-02)
bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
forwarded_allow_ips = os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1,::1")
backlog = 2048

# Worker processes (2 * cores + 1, capped conservatively for medical research ML workload)
default_workers = min(multiprocessing.cpu_count() * 2 + 1, 8)
workers = int(os.environ.get("GUNICORN_WORKERS", default_workers))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 60
keepalive = 5

# Graceful restart & reload
graceful_timeout = 30
max_requests = 5000
max_requests_jitter = 500

# Logging
accesslog = os.environ.get("GUNICORN_ACCESS_LOG", "/var/log/heartai/access.log")
errorlog = os.environ.get("GUNICORN_ERROR_LOG", "/var/log/heartai/error.log")
loglevel = os.environ.get("LOG_LEVEL", "info").lower()

# Security & Process Name
proc_name = "heartai-gunicorn"
daemon = False
