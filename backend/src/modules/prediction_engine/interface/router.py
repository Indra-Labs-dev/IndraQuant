from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.composition_root import (
    get_current_user,
    get_manage_training_use_case,
    get_predict_direction_use_case,
    get_prediction_dashboard_use_case,
)
from src.modules.auth.application.dto import UserProfile
from src.modules.machine_learning.application.dto import DirectionPrediction
from src.modules.prediction_engine.application.use_cases.get_prediction_dashboard import (
    GetPredictionDashboardUseCase,
    PredictionDashboard,
)
from src.modules.prediction_engine.application.use_cases.manage_training import (
    ManageTrainingUseCase,
    TrainingSessionsResponse,
)
from src.modules.prediction_engine.application.use_cases.predict_direction import (
    PredictDirectionUseCase,
)

router = APIRouter(tags=["prediction"])


class TrainingSessionRequest(BaseModel):
    timeframe: str
    instrument_ids: list[int]


@router.get("/instruments/{instrument_id}/prediction")
def get_prediction(
    instrument_id: int,
    timeframe: str = Query(default="1h"),
    _: UserProfile = Depends(get_current_user),
    use_case: PredictDirectionUseCase = Depends(get_predict_direction_use_case),
) -> DirectionPrediction:
    return use_case.execute(instrument_id, timeframe)


@router.get("/predictions/dashboard")
def get_prediction_dashboard(
    timeframe: str = Query(default="1h"),
    instrument_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: UserProfile = Depends(get_current_user),
    use_case: GetPredictionDashboardUseCase = Depends(get_prediction_dashboard_use_case),
) -> PredictionDashboard:
    return use_case.execute(timeframe, instrument_id, limit)


@router.post("/training/start")
def start_training(
    request: TrainingSessionRequest,
    _: UserProfile = Depends(get_current_user),
    use_case: ManageTrainingUseCase = Depends(get_manage_training_use_case),
) -> TrainingSessionsResponse:
    return use_case.start(request.timeframe, request.instrument_ids)


@router.post("/training/stop")
def stop_training(
    request: TrainingSessionRequest,
    _: UserProfile = Depends(get_current_user),
    use_case: ManageTrainingUseCase = Depends(get_manage_training_use_case),
) -> TrainingSessionsResponse:
    return use_case.stop(request.timeframe, request.instrument_ids)


@router.get("/training/sessions")
def get_training_sessions(
    _: UserProfile = Depends(get_current_user),
    use_case: ManageTrainingUseCase = Depends(get_manage_training_use_case),
) -> TrainingSessionsResponse:
    return use_case.list_sessions()
