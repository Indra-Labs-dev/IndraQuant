from fastapi import APIRouter, Depends, Query

from src.composition_root import get_current_user, get_market_regime_use_case
from src.modules.auth.application.dto import UserProfile
from src.modules.market_regime.application.dto import MarketRegimeResponse
from src.modules.market_regime.application.use_cases.get_market_regime import (
    GetMarketRegimeUseCase,
)

router = APIRouter(tags=["market-regime"])


@router.get("/instruments/{instrument_id}/market-regime")
async def get_market_regime(
    instrument_id: int,
    timeframe: str = Query(default="1h"),
    _: UserProfile = Depends(get_current_user),
    use_case: GetMarketRegimeUseCase = Depends(get_market_regime_use_case),
) -> MarketRegimeResponse:
    return await use_case.execute(instrument_id, timeframe)
