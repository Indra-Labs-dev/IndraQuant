from datetime import datetime, timezone
from decimal import Decimal

import ccxt

from src.modules.market_data.domain.aggregation import aggregate_candles
from src.modules.market_data.domain.entities import Candle, Instrument
from src.modules.market_data.domain.value_objects import Timeframe
from src.shared.kernel.errors import AppError

# Sub-minute timeframes not offered natively by exchanges are rebuilt from
# 1s candles (ADR-015).
_AGGREGATED_TIMEFRAMES = {"5s": 5, "30s": 30}


class CcxtMarketDataRepository:
    """Multi-exchange crypto adapter (ADR-003): the target exchange comes
    from the instrument itself, never hardcoded."""

    def __init__(self) -> None:
        self._clients: dict[str, ccxt.Exchange] = {}

    def _client(self, ccxt_id: str) -> ccxt.Exchange:
        if ccxt_id not in self._clients:
            if not hasattr(ccxt, ccxt_id):
                raise AppError(
                    "unknown_exchange", f"Exchange ccxt inconnu : {ccxt_id}", 500
                )
            self._clients[ccxt_id] = getattr(ccxt, ccxt_id)(
                {"enableRateLimit": True}
            )
        return self._clients[ccxt_id]

    def fetch_ohlcv(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        since: datetime,
        limit: int,
    ) -> list[Candle]:
        bucket_seconds = _AGGREGATED_TIMEFRAMES.get(timeframe.value)
        if bucket_seconds is not None:
            fine = self.fetch_ohlcv(instrument, Timeframe("1s"), since, limit)
            return aggregate_candles(fine, bucket_seconds)

        client = self._client(instrument.exchange_ccxt_id)
        if client.timeframes and timeframe.value not in client.timeframes:
            raise AppError(
                "timeframe_unsupported",
                f"L'exchange {instrument.exchange_ccxt_id} ne fournit pas "
                f"le timeframe {timeframe.value}.",
                http_status=422,
            )
        since_ms = int(since.replace(tzinfo=timezone.utc).timestamp() * 1000)
        try:
            rows = client.fetch_ohlcv(
                instrument.symbol, timeframe.value, since=since_ms, limit=limit
            )
        except ccxt.BaseError as error:
            raise AppError(
                "market_data_unavailable",
                f"Échec de récupération depuis {instrument.exchange_ccxt_id} : {error}",
                http_status=502,
            )
        return [
            Candle(
                open_time=datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc).replace(
                    tzinfo=None
                ),
                open=Decimal(str(row[1])),
                high=Decimal(str(row[2])),
                low=Decimal(str(row[3])),
                close=Decimal(str(row[4])),
                volume=Decimal(str(row[5])),
            )
            for row in rows
        ]
