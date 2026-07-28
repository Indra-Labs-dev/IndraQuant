from datetime import datetime

from fastapi import APIRouter, Depends, Query

from src.composition_root import (
    get_compute_indicators_use_case,
    get_current_user,
    get_volume_profile_use_case,
)
from src.modules.auth.application.dto import UserProfile
from src.modules.technical_analysis.application.dto import (
    IndicatorsResponse,
    VolumeProfileResponse,
)
from src.modules.technical_analysis.application.use_cases.compute_indicators import (
    ComputeIndicatorsUseCase,
)
from src.modules.technical_analysis.application.use_cases.get_volume_profile import (
    GetVolumeProfileUseCase,
)

router = APIRouter(prefix="/instruments", tags=["technical-analysis"])


@router.get("/{instrument_id}/indicators")
async def get_indicators(
    instrument_id: int,
    timeframe: str = Query(),
    from_: datetime = Query(alias="from"),
    to: datetime = Query(),
    limit: int = Query(default=500, ge=1, le=5000),
    indicators: str = Query(
        default="sma:20,sma:50,rsi:14",
        description="CSV of name[:period], e.g. sma:20,ema:12,rsi:14,macd,bollinger:20",
    ),
    _: UserProfile = Depends(get_current_user),
    use_case: ComputeIndicatorsUseCase = Depends(get_compute_indicators_use_case),
) -> IndicatorsResponse:
    specs = [s for s in indicators.split(",") if s.strip()]
    return await use_case.execute(instrument_id, timeframe, from_, to, limit, specs)


@router.get("/{instrument_id}/volume-profile")
async def get_volume_profile(
    instrument_id: int,
    timeframe: str = Query(),
    from_: datetime = Query(alias="from"),
    to: datetime = Query(),
    limit: int = Query(default=500, ge=1, le=5000),
    bins: int = Query(default=10, ge=3, le=50),
    _: UserProfile = Depends(get_current_user),
    use_case: GetVolumeProfileUseCase = Depends(get_volume_profile_use_case),
) -> VolumeProfileResponse:
    return await use_case.execute(instrument_id, timeframe, from_, to, limit, bins)
