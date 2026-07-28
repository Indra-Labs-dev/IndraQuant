from fastapi import APIRouter, Depends, Query

from src.composition_root import get_correlation_matrix_use_case, get_current_user
from src.modules.auth.application.dto import UserProfile
from src.modules.correlation_engine.application.dto import CorrelationMatrixResponse
from src.modules.correlation_engine.application.use_cases.get_correlation_matrix import (
    GetCorrelationMatrixUseCase,
)
from src.shared.kernel.errors import AppError

router = APIRouter(tags=["correlation-engine"])


@router.get("/correlations")
async def get_correlations(
    instrument_ids: str = Query(
        ..., description="Identifiants d'instruments séparés par des virgules, ex. 1,2,3"
    ),
    timeframe: str = Query(default="1h"),
    window: int = Query(default=20, ge=2, le=200),
    _: UserProfile = Depends(get_current_user),
    use_case: GetCorrelationMatrixUseCase = Depends(get_correlation_matrix_use_case),
) -> CorrelationMatrixResponse:
    try:
        ids = [int(part) for part in instrument_ids.split(",") if part.strip()]
    except ValueError:
        raise AppError(
            "invalid_request",
            "instrument_ids doit être une liste d'identifiants entiers séparés par des virgules.",
            422,
        )
    return await use_case.execute(ids, timeframe, window)
