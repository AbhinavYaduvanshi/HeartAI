"""HeartAI Primary Prediction Endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_optional_current_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.models import User
from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.services.prediction_service import process_cardiovascular_prediction

router = APIRouter(tags=["Educational Risk Estimation"])


@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Calibrated Cardiovascular Disease Probability",
)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
def predict_cardiovascular_risk(
    request: Request,
    payload: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> PredictionResponse:
    """Calculates continuous calibrated probability of reported historical CVD.

    - Validates 25 CDC BRFSS physiological, demographic, and behavioral features.
    - Applies calibrated operating threshold (T = 0.09) for binary classification flag.
    - Persists audit record if and only if explicit user consent is provided.
    - Strictly reports 'Estimated probability of reported historical cardiovascular disease'.
    """
    return process_cardiovascular_prediction(
        request=payload,
        db=db,
        current_user=current_user,
    )
