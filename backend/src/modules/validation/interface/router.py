from fastapi import APIRouter, Depends, Query

from src.composition_root import (
    get_current_user,
    get_validate_backtest_use_case,
    get_validate_model_use_case,
)
from src.modules.auth.application.dto import UserProfile
from src.modules.backtesting.application.dto import RunBacktestRequest
from src.modules.validation.application.dto import (
    BacktestValidationResponse,
    ModelValidationResponse,
)
from src.modules.validation.application.use_cases.validate_backtest import (
    ValidateBacktestUseCase,
)
from src.modules.validation.application.use_cases.validate_model import (
    ValidatePredictionModelUseCase,
)

router = APIRouter(tags=["validation"])


@router.get("/instruments/{instrument_id}/model-validation")
async def get_model_validation(
    instrument_id: int,
    timeframe: str = Query(default="1h"),
    _: UserProfile = Depends(get_current_user),
    use_case: ValidatePredictionModelUseCase = Depends(get_validate_model_use_case),
) -> ModelValidationResponse:
    return await use_case.execute(instrument_id, timeframe)


@router.post("/backtests/validation")
async def validate_backtest(
    request: RunBacktestRequest,
    _: UserProfile = Depends(get_current_user),
    use_case: ValidateBacktestUseCase = Depends(get_validate_backtest_use_case),
) -> BacktestValidationResponse:
    return await use_case.execute(request)
