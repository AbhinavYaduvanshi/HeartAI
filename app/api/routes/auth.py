"""HeartAI Authentication, User Accounts and History Endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import PredictionRecord, User
from app.schemas.user import PredictionHistoryItem, Token, UserCreate, UserLogin, UserResponse

router = APIRouter(tags=["User Accounts & Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a New User Account",
)
def register_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Registers a new researcher or clinician account."""
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
def login_user(
    payload: UserLogin,
    db: Session = Depends(get_db),
) -> Token:
    """Authenticates credentials and issues a signed JSON Web Token (JWT)."""
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
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
