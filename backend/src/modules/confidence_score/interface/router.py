from fastapi import APIRouter, Depends, Query

from src.composition_root import get_current_user, get_global_confidence_score_use_case
from src.modules.auth.application.dto import UserProfile
from src.modules.confidence_score.application.dto import GlobalConfidenceResponse
from src.modules.confidence_score.application.use_cases.get_global_confidence import (
    GetGlobalConfidenceScoreUseCase,
)

router = APIRouter(tags=["confidence-score"])


@router.get("/instruments/{instrument_id}/confidence-score")
def get_global_confidence_score(
    instrument_id: int,
    timeframe: str = Query(default="1h"),
    _: UserProfile = Depends(get_current_user),
    use_case: GetGlobalConfidenceScoreUseCase = Depends(get_global_confidence_score_use_case),
) -> GlobalConfidenceResponse:
    return use_case.execute(instrument_id, timeframe)
