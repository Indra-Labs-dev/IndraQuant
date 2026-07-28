from datetime import datetime

from fastapi import APIRouter, Depends, Query

from src.composition_root import (
    get_current_user,
    get_list_instruments_use_case,
    get_market_status_use_case,
    get_ohlcv_use_case,
)
from src.modules.auth.application.dto import UserProfile
from src.modules.market_data.application.dto import InstrumentsResponse, OhlcvResponse
from src.modules.market_data.application.use_cases.get_market_status import (
    GetMarketStatusUseCase,
    MarketStatusResponse,
)
from src.modules.market_data.application.use_cases.get_ohlcv import GetOhlcvUseCase
from src.modules.market_data.application.use_cases.list_instruments import (
    ListInstrumentsUseCase,
)

router = APIRouter(prefix="/instruments", tags=["market-data"])


@router.get("")
async def list_instruments(
    asset_class: str | None = Query(default=None),
    exchange: str | None = Query(default=None),
    _: UserProfile = Depends(get_current_user),
    use_case: ListInstrumentsUseCase = Depends(get_list_instruments_use_case),
) -> InstrumentsResponse:
    return await use_case.execute(asset_class, exchange)


@router.get("/{instrument_id}/market-status")
async def get_market_status(
    instrument_id: int,
    _: UserProfile = Depends(get_current_user),
    use_case: GetMarketStatusUseCase = Depends(get_market_status_use_case),
) -> MarketStatusResponse:
    return await use_case.execute(instrument_id)


@router.get("/{instrument_id}/ohlcv")
async def get_ohlcv(
    instrument_id: int,
    timeframe: str = Query(),
    from_: datetime = Query(alias="from"),
    to: datetime = Query(),
    limit: int = Query(default=500, ge=1, le=5000),
    _: UserProfile = Depends(get_current_user),
    use_case: GetOhlcvUseCase = Depends(get_ohlcv_use_case),
) -> OhlcvResponse:
    return await use_case.execute(instrument_id, timeframe, from_, to, limit)
