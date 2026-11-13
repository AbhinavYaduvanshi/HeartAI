"""HeartAI SQLAlchemy ORM Database Models.

Stores user credentials and privacy-compliant, consent-gated prediction history.
"""

from __future__ import annotations

import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class User(Base):
    """User account entity for authenticated physicians and researchers."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=datetime.datetime.utcnow)

    # Relationships
    predictions = relationship("PredictionRecord", back_populates="user", cascade="all, delete-orphan")


class PredictionRecord(Base):
    """Audit record for educational risk predictions with explicit user consent."""

    __tablename__ = "prediction_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    anonymized_input_hash = Column(String(64), nullable=False, index=True)
    estimated_probability = Column(Float, nullable=False)
    binary_classification = Column(Integer, nullable=False)
    operating_threshold = Column(Float, default=0.09, nullable=False)
    model_version = Column(String(32), default="2.1.0", nullable=False)
    user_consent_given = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="predictions")
