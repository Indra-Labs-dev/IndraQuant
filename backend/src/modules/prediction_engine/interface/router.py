from fastapi import APIRouter, Depends, Query

from src.composition_root import get_current_user, get_predict_direction_use_case
from src.modules.auth.application.dto import UserProfile
from src.modules.machine_learning.application.dto import DirectionPrediction
from src.modules.prediction_engine.application.use_cases.predict_direction import (
    PredictDirectionUseCase,
)

router = APIRouter(prefix="/instruments", tags=["prediction"])


@router.get("/{instrument_id}/prediction")
def get_prediction(
    instrument_id: int,
    timeframe: str = Query(default="1h"),
    _: UserProfile = Depends(get_current_user),
    use_case: PredictDirectionUseCase = Depends(get_predict_direction_use_case),
) -> DirectionPrediction:
    return use_case.execute(instrument_id, timeframe)
