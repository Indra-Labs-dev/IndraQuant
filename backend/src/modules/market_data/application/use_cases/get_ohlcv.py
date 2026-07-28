from datetime import datetime, timezone

from src.modules.market_data.application.dto import CandleDto, OhlcvResponse
from src.modules.market_data.domain.repositories import (
    CandleStore,
    InstrumentRepository,
    MarketDataRepository,
)
from src.modules.market_data.domain.value_objects import Timeframe
from src.shared.events.event_bus import EventBus, MarketDataIngested
from src.shared.kernel.errors import AppError, NotFoundError

_FETCH_PAGE_SIZE = 1000
_MAX_FETCH_PAGES = 10
# Every OHLCV read goes through this ingestion check first, and it is called
# from nearly every module (predictions, meta-decision, correlations,
# indicators, SMC...). Without debouncing, N concurrent requests for the
# same instrument/timeframe each independently re-hit the external provider
# and re-upsert the same still-forming candle, which is exactly what causes
# InnoDB lock-wait timeouts under load (docs/roadmap #17 — optimisation des
# écritures en base). The cooldown is short enough that the live candle is
# still refreshed well within human-perceptible latency.
_INGEST_COOLDOWN_SECONDS = 2


def _to_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


class GetOhlcvUseCase:
    """Read-through: serves candles from storage, fetching what is missing
    from the external market data source first (idempotent upsert, so
    ingestion is replayable — docs/01 success criteria)."""

    def __init__(
        self,
        instruments: InstrumentRepository,
        provider: MarketDataRepository,
        store: CandleStore,
        events: EventBus,
        clock: type[datetime] = datetime,
        cache=None,
    ) -> None:
        self._instruments = instruments
        self._provider = provider
        self._store = store
        self._events = events
        self._clock = clock
        self._cache = cache

    async def execute(
        self,
        instrument_id: int,
        timeframe_value: str,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> OhlcvResponse:
        try:
            timeframe = Timeframe(timeframe_value)
        except ValueError as error:
            raise AppError("invalid_timeframe", str(error), http_status=422)

        start, end = _to_naive_utc(start), _to_naive_utc(end)
        if start >= end:
            raise AppError(
                "invalid_range", "Parameter 'from' must be before 'to'.", 422
            )

        instrument = await self._instruments.get(instrument_id)
        if instrument is None:
            raise NotFoundError(
                "instrument_not_found", f"Instrument {instrument_id} inconnu."
            )

        await self._ingest_missing(instrument, timeframe, start, end)

        candles = await self._store.get_range(instrument_id, timeframe, start, end, limit)
        return OhlcvResponse(
            instrument_id=instrument_id,
            timeframe=timeframe.value,
            candles=[
                CandleDto(
                    open_time=c.open_time.replace(tzinfo=timezone.utc),
                    open=float(c.open),
                    high=float(c.high),
                    low=float(c.low),
                    close=float(c.close),
                    volume=float(c.volume),
                )
                for c in candles
            ],
        )

    async def _ingest_missing(self, instrument, timeframe, start, end) -> None:
        now = _to_naive_utc(self._clock.now(timezone.utc))
        latest = await self._store.latest_open_time(instrument.id, timeframe)
        earliest = await self._store.earliest_open_time(instrument.id, timeframe)

        total = 0
        if earliest is not None and start < earliest:
            # Backfill history older than what is stored.
            total += await self._fetch_range(instrument, timeframe, start, earliest)

        # Refetch from the latest stored candle (it may have been partial
        # when first ingested); from `start` when storage is empty.
        forward_since = start if latest is None else latest
        if forward_since < min(end, now) and await self._should_attempt_ingest(
            instrument.id, timeframe.value
        ):
            total += await self._fetch_range(instrument, timeframe, forward_since, end)

        if total:
            self._events.publish(
                MarketDataIngested(
                    instrument_id=instrument.id,
                    timeframe=timeframe.value,
                    candle_count=total,
                    ingested_at=now,
                )
            )

    async def _should_attempt_ingest(self, instrument_id: int, timeframe_value: str) -> bool:
        if self._cache is None:
            return True
        try:
            key = f"ohlcv-ingest-cooldown:{instrument_id}:{timeframe_value}"
            return bool(await self._cache.set(key, "1", nx=True, ex=_INGEST_COOLDOWN_SECONDS))
        except Exception:
            return True

    async def _fetch_range(self, instrument, timeframe, since, until) -> int:
        total = 0
        for _ in range(_MAX_FETCH_PAGES):
            batch = self._provider.fetch_ohlcv(
                instrument, timeframe, since, _FETCH_PAGE_SIZE
            )
            if not batch:
                break
            total += await self._store.upsert_many(instrument.id, timeframe, batch)
            last_open = batch[-1].open_time
            if last_open >= until or len(batch) < _FETCH_PAGE_SIZE:
                break
            since = last_open
        return total
