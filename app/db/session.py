"""HeartAI Database Engine and Session Management.

Provides SQLAlchemy 2.0 ORM session lifecycles with SQLite and PostgreSQL support.
"""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

logger = logging.getLogger("heartai.db")

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db() -> Generator:
    """Dependency that yields a managed SQLAlchemy database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> tuple[bool, str]:
    """Tests the database connection, returning (is_connected, dialect_name)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True, engine.dialect.name
    except Exception as err:
        logger.warning("Database connectivity check failed: %s", err)
        return False, engine.dialect.name


def init_db() -> None:
    """Creates database tables if they do not exist."""
    # Import models to ensure they are registered with Base.metadata
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully (dialect: %s).", engine.dialect.name)
