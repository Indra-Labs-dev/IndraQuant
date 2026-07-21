from datetime import datetime

from fastapi import APIRouter, Depends, Query

from src.composition_root import (
    get_current_user,
    get_list_instruments_use_case,
    get_ohlcv_use_case,
)
from src.modules.auth.application.dto import UserProfile
from src.modules.market_data.application.dto import InstrumentsResponse, OhlcvResponse
from src.modules.market_data.application.use_cases.get_ohlcv import GetOhlcvUseCase
from src.modules.market_data.application.use_cases.list_instruments import (
    ListInstrumentsUseCase,
)

router = APIRouter(prefix="/instruments", tags=["market-data"])


@router.get("")
def list_instruments(
    asset_class: str | None = Query(default=None),
    exchange: str | None = Query(default=None),
    _: UserProfile = Depends(get_current_user),
    use_case: ListInstrumentsUseCase = Depends(get_list_instruments_use_case),
) -> InstrumentsResponse:
    return use_case.execute(asset_class, exchange)


@router.get("/{instrument_id}/ohlcv")
def get_ohlcv(
    instrument_id: int,
    timeframe: str = Query(),
    from_: datetime = Query(alias="from"),
    to: datetime = Query(),
    limit: int = Query(default=500, ge=1, le=5000),
    _: UserProfile = Depends(get_current_user),
    use_case: GetOhlcvUseCase = Depends(get_ohlcv_use_case),
) -> OhlcvResponse:
    return use_case.execute(instrument_id, timeframe, from_, to, limit)
