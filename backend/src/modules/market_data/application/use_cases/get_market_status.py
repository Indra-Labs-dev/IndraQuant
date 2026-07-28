from datetime import datetime, timezone

from pydantic import BaseModel

from src.modules.market_data.domain.repositories import InstrumentRepository
from src.modules.market_data.domain.trading_calendar import (
    crypto_market_status,
    equity_market_status,
)
from src.shared.kernel.errors import NotFoundError


class MarketStatusResponse(BaseModel):
    instrument_id: int
    asset_class: str
    is_open: bool
    next_open: datetime | None
    next_close: datetime | None


class GetMarketStatusUseCase:
    def __init__(self, instruments: InstrumentRepository) -> None:
        self._instruments = instruments

    async def execute(self, instrument_id: int) -> MarketStatusResponse:
        instrument = await self._instruments.get(instrument_id)
        if instrument is None:
            raise NotFoundError(
                "instrument_not_found", f"Instrument {instrument_id} inconnu."
            )

        status = (
            crypto_market_status()
            if instrument.asset_class == "crypto"
            else equity_market_status(datetime.now(timezone.utc))
        )
        return MarketStatusResponse(
            instrument_id=instrument_id,
            asset_class=instrument.asset_class,
            is_open=status.is_open,
            next_open=status.next_open,
            next_close=status.next_close,
        )
