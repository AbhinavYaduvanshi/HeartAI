"""HeartAI Authentication, User Accounts and History Endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    hash_password,
    verify_dummy_password,
    verify_password,
)
from app.db.models import PredictionRecord, User
from app.schemas.user import (
    PredictionHistoryItem,
    Token,
    UserConsentResponse,
    UserConsentUpdate,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.consent_service import record_user_consent

router = APIRouter(tags=["User Accounts & Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a New User Account",
)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def register_user(
    request: Request,
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Registers a new researcher or clinician account with rate-limiting."""
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Authenticate User and Generate JWT Token",
)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def login_user(
    request: Request,
    payload: UserLogin,
    db: Session = Depends(get_db),
) -> Token:
    """Authenticates credentials in constant time and issues a signed JSON Web Token (JWT)."""
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user:
        # Constant-time dummy hash computation to mitigate user enumeration timing attacks
        verify_dummy_password(payload.password)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    token = create_access_token(subject=user.email)
    return Token(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Authenticated User Profile",
)
def get_authenticated_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Returns profile for currently authenticated user."""
    return current_user


@router.get(
    "/consent",
    response_model=UserConsentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Trusted Consent Status for Authenticated User",
)
def get_user_consent_status(
    current_user: User = Depends(get_current_user),
) -> UserConsentResponse:
    """Returns the verified server-side consent state for the authenticated user."""
    return UserConsentResponse(
        consent_given=bool(current_user.consent_given),
        consent_terms_version=current_user.consent_terms_version,
        consent_revoked=bool(current_user.consent_revoked),
        consent_updated_at=current_user.consent_updated_at,
    )


@router.post(
    "/consent",
    response_model=UserConsentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Trusted Consent State for Authenticated User",
)
def update_user_consent_status(
    payload: UserConsentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserConsentResponse:
    """Records or revokes informed consent in the trusted database record."""
    updated_user = record_user_consent(
        user=current_user,
        db=db,
        consent_given=payload.consent_given,
        terms_version=payload.terms_version,
    )
    return UserConsentResponse(
        consent_given=bool(updated_user.consent_given),
        consent_terms_version=updated_user.consent_terms_version,
        consent_revoked=bool(updated_user.consent_revoked),
        consent_updated_at=updated_user.consent_updated_at,
    )


@router.get(
    "/history",
    response_model=list[PredictionHistoryItem],
    status_code=status.HTTP_200_OK,
    summary="Get Prediction History for Authenticated User",
)
def get_user_prediction_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PredictionHistoryItem]:
    """Retrieves consent-given historical predictions for current user."""
    records = (
        db.query(PredictionRecord)
        .filter(PredictionRecord.user_id == current_user.id)
        .order_by(PredictionRecord.created_at.desc())
        .limit(100)
        .all()
    )
    return records


@router.delete(
    "/history",
    status_code=status.HTTP_200_OK,
    summary="Purge All Prediction History for Authenticated User",
)
def purge_user_prediction_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Provides user prediction history deletion functionality supporting privacy and data subject erasure workflows."""
    deleted_count = (
        db.query(PredictionRecord)
        .filter(PredictionRecord.user_id == current_user.id)
        .delete()
    )
    db.commit()
    return {
        "status": "success",
        "deleted_count": deleted_count,
        "message": f"Successfully purged {deleted_count} prediction audit records.",
    }


@router.delete(
    "/history/{record_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Specific Prediction Record for Authenticated User",
)
def delete_single_prediction_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes a single prediction audit record belonging to the authenticated user."""
    record = (
        db.query(PredictionRecord)
        .filter(
            PredictionRecord.id == record_id,
            PredictionRecord.user_id == current_user.id,
        )
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction record not found or access denied.",
        )
    db.delete(record)
    db.commit()
    return {
        "status": "success",
        "deleted_id": record_id,
        "message": f"Record {record_id} successfully deleted.",
    }
