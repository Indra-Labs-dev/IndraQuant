from datetime import datetime
from typing import Protocol

from src.modules.market_data.domain.entities import Candle, Instrument
from src.modules.market_data.domain.value_objects import Timeframe


class MarketDataRepository(Protocol):
    """External market data source (docs/04 — Repository Pattern, ADR-003/004)."""

    def fetch_ohlcv(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        since: datetime,
        limit: int,
    ) -> list[Candle]: ...


class InstrumentRepository(Protocol):
    async def list_instruments(
        self, asset_class: str | None = None, exchange: str | None = None
    ) -> list[Instrument]: ...

    async def get(self, instrument_id: int) -> Instrument | None: ...


class CandleStore(Protocol):
    """Historical Data Storage persistence port."""

    async def get_range(
        self,
        instrument_id: int,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[Candle]: ...

    async def latest_open_time(
        self, instrument_id: int, timeframe: Timeframe
    ) -> datetime | None: ...

    async def earliest_open_time(
        self, instrument_id: int, timeframe: Timeframe
    ) -> datetime | None: ...

    async def upsert_many(
        self, instrument_id: int, timeframe: Timeframe, candles: list[Candle]
    ) -> int: ...
