"""User Authentication and Account Schemas."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Payload for registering a new user account."""

    email: EmailStr = Field(..., description="Valid user email address")
    password: str = Field(..., min_length=8, description="Account password (minimum 8 characters)")


class UserLogin(BaseModel):
    """Payload for authenticating and receiving an access token."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """Public user profile information."""

    id: int
    email: str
    is_active: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Bearer access token payload."""

    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class PredictionHistoryItem(BaseModel):
    """Historic prediction record item for authenticated user."""

    id: int
    estimated_probability: float
    binary_classification: int
    operating_threshold: float
    model_version: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

