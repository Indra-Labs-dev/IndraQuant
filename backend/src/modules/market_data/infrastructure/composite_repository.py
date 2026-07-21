from datetime import datetime

from src.modules.market_data.domain.entities import Candle, Instrument
from src.modules.market_data.domain.repositories import MarketDataRepository
from src.modules.market_data.domain.value_objects import Timeframe
from src.shared.kernel.errors import AppError


class CompositeMarketDataRepository:
    """Routes each instrument to the adapter of its asset class — the
    application layer stays unaware of how many adapters exist (ADR-004)."""

    def __init__(self, adapters: dict[str, MarketDataRepository]) -> None:
        self._adapters = adapters

    def fetch_ohlcv(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        since: datetime,
        limit: int,
    ) -> list[Candle]:
        adapter = self._adapters.get(instrument.asset_class)
        if adapter is None:
            raise AppError(
                "asset_class_unsupported",
                f"Aucun adaptateur pour la classe d'actifs "
                f"{instrument.asset_class}.",
                http_status=422,
            )
        return adapter.fetch_ohlcv(instrument, timeframe, since, limit)
