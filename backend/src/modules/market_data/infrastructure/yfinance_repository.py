from datetime import datetime, timezone
from decimal import Decimal

from src.modules.market_data.domain.entities import Candle, Instrument
from src.modules.market_data.domain.value_objects import Timeframe
from src.shared.kernel.errors import AppError

# Yahoo Finance intervals: no seconds, no 4h.
_INTERVALS = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "1d": "1d"}


class YFinanceMarketDataRepository:
    """Equities adapter (Phase 5) — same MarketDataRepository port as the
    crypto adapter, proving the multi-asset architecture (ADR-004)."""

    def fetch_ohlcv(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        since: datetime,
        limit: int,
    ) -> list[Candle]:
        interval = _INTERVALS.get(timeframe.value)
        if interval is None:
            raise AppError(
                "timeframe_unsupported",
                f"Yahoo Finance ne fournit pas le timeframe {timeframe.value} "
                f"(disponibles : {', '.join(_INTERVALS)}).",
                http_status=422,
            )

        import yfinance as yf

        try:
            frame = yf.Ticker(instrument.symbol).history(
                start=since.replace(tzinfo=timezone.utc),
                interval=interval,
                auto_adjust=False,
            )
        except Exception as error:
            raise AppError(
                "market_data_unavailable",
                f"Échec de récupération Yahoo Finance : {error}",
                http_status=502,
            )

        candles: list[Candle] = []
        for index, row in frame.iterrows():
            open_time = index.to_pydatetime()
            if open_time.tzinfo is not None:
                open_time = open_time.astimezone(timezone.utc).replace(tzinfo=None)
            candles.append(
                Candle(
                    open_time=open_time,
                    open=Decimal(str(round(float(row["Open"]), 8))),
                    high=Decimal(str(round(float(row["High"]), 8))),
                    low=Decimal(str(round(float(row["Low"]), 8))),
                    close=Decimal(str(round(float(row["Close"]), 8))),
                    volume=Decimal(str(round(float(row["Volume"]), 8))),
                )
            )
        return candles[:limit]
