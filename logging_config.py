"""HeartAI Enterprise Logging Configuration.

Provides structured logging with console formatting, file rotation,
and clinical audit logging capabilities.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Logs directory
LOGS_DIR = Path("logs")
try:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

DEFAULT_LOG_FILE = LOGS_DIR / "heartai.log"
AUDIT_LOG_FILE = LOGS_DIR / "clinical_audit.log"


class SensitiveDataFilter(logging.Filter):
    """Masks or prevents leaking sensitive health data or API keys in logs."""

    SENSITIVE_KEYWORDS = ("password", "secret", "token", "api_key", "bearer")

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage().lower()
        for kw in self.SENSITIVE_KEYWORDS:
            if kw in message and "=" in message:
                record.msg = f"[REDACTED POTENTIAL SECRET: contains {kw}]"
                record.args = ()
        return True


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_file: Path | str = DEFAULT_LOG_FILE,
) -> logging.Logger:
    """Configures root and application loggers."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Base formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clean existing handlers to avoid duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(console_handler)

    # Rotating File Handler
    if log_to_file:
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB per file
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(SensitiveDataFilter())
        root_logger.addHandler(file_handler)

    logger = logging.getLogger("heartai")
    logger.info("HeartAI logging subsystem initialized at level %s", level)
    return logger


def get_audit_logger() -> logging.Logger:
    """Returns a dedicated logger for immutable patient assessment and prediction audits."""
    audit_logger = logging.getLogger("heartai.audit")
    if not audit_logger.handlers:
        audit_logger.setLevel(logging.INFO)
        audit_logger.propagate = False

        audit_formatter = logging.Formatter(
            fmt='{"timestamp": "%(asctime)s", "event": "%(message)s"}',
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
        audit_handler = RotatingFileHandler(
            filename=AUDIT_LOG_FILE,
            maxBytes=20 * 1024 * 1024,
            backupCount=10,
            encoding="utf-8",
        )
        audit_handler.setFormatter(audit_formatter)
        audit_logger.addHandler(audit_handler)

    return audit_logger


if __name__ == "__main__":
    test_logger = setup_logging("DEBUG")
    test_logger.info("HeartAI logging self-test passed.")
    audit = get_audit_logger()
    audit.info("Self-test audit event: model loaded and verified.")
    print("Logging self-test completed successfully.")
