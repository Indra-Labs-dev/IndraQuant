from datetime import datetime

from fastapi import APIRouter, Depends, Query

from src.composition_root import get_current_user, get_detect_smc_use_case
from src.modules.auth.application.dto import UserProfile
from src.modules.smart_money.application.use_cases.detect_smc import (
    DetectSmcUseCase,
    SmcResponse,
)

router = APIRouter(prefix="/instruments", tags=["smart-money"])


@router.get("/{instrument_id}/smc")
def get_smc(
    instrument_id: int,
    timeframe: str = Query(),
    from_: datetime = Query(alias="from"),
    to: datetime = Query(),
    limit: int = Query(default=500, ge=1, le=5000),
    _: UserProfile = Depends(get_current_user),
    use_case: DetectSmcUseCase = Depends(get_detect_smc_use_case),
) -> SmcResponse:
    return use_case.execute(instrument_id, timeframe, from_, to, limit)
