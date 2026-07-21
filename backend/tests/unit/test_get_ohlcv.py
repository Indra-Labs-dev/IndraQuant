from datetime import datetime
from decimal import Decimal

import pytest

from src.modules.market_data.application.use_cases.get_ohlcv import GetOhlcvUseCase
from src.modules.market_data.domain.entities import Candle, Instrument
from src.shared.events.event_bus import EventBus, MarketDataIngested
from src.shared.kernel.errors import AppError, NotFoundError

BTC = Instrument(
    id=1,
    exchange_ccxt_id="binance",
    exchange_display_name="Binance",
    symbol="BTC/USDT",
    base_asset="BTC",
    quote_asset="USDT",
    asset_class="crypto",
    is_active=True,
)


def candle(open_time: datetime, price: str = "100") -> Candle:
    value = Decimal(price)
    return Candle(
        open_time=open_time, open=value, high=value, low=value, close=value, volume=value
    )


class FakeInstruments:
    def __init__(self, instruments: list[Instrument]) -> None:
        self._instruments = instruments

    def list_instruments(self, asset_class=None, exchange=None):
        return self._instruments

    def get(self, instrument_id: int) -> Instrument | None:
        return next((i for i in self._instruments if i.id == instrument_id), None)


class FakeProvider:
    def __init__(self, batches: list[list[Candle]]) -> None:
        self._batches = batches
        self.calls: list[datetime] = []

    def fetch_ohlcv(self, instrument, timeframe, since, limit):
        self.calls.append(since)
        return self._batches.pop(0) if self._batches else []


class FakeStore:
    def __init__(self, candles: list[Candle] | None = None) -> None:
        self.candles: list[Candle] = candles or []

    def get_range(self, instrument_id, timeframe, start, end, limit):
        return sorted(
            (c for c in self.candles if start <= c.open_time <= end),
            key=lambda c: c.open_time,
        )[:limit]

    def latest_open_time(self, instrument_id, timeframe):
        return max((c.open_time for c in self.candles), default=None)

    def earliest_open_time(self, instrument_id, timeframe):
        return min((c.open_time for c in self.candles), default=None)

    def upsert_many(self, instrument_id, timeframe, candles):
        existing = {c.open_time for c in self.candles}
        self.candles.extend(c for c in candles if c.open_time not in existing)
        return len(candles)


def make_use_case(provider: FakeProvider, store: FakeStore, bus: EventBus | None = None):
    return GetOhlcvUseCase(
        FakeInstruments([BTC]), provider, store, bus or EventBus()
    )


def test_empty_store_triggers_fetch_from_start_and_publishes_event():
    fetched = [candle(datetime(2026, 1, 1, h)) for h in range(3)]
    provider = FakeProvider([fetched])
    store = FakeStore()
    bus = EventBus()
    events: list[MarketDataIngested] = []
    bus.subscribe(MarketDataIngested, events.append)

    response = make_use_case(provider, store, bus).execute(
        1, "1h", datetime(2026, 1, 1), datetime(2026, 1, 2), 500
    )

    assert provider.calls == [datetime(2026, 1, 1)]
    assert len(response.candles) == 3
    assert len(events) == 1
    assert events[0].candle_count == 3


def test_fetch_resumes_from_latest_stored_candle():
    store = FakeStore([candle(datetime(2026, 1, 1, 0)), candle(datetime(2026, 1, 1, 1))])
    provider = FakeProvider([[candle(datetime(2026, 1, 1, h)) for h in (1, 2, 3)]])

    response = make_use_case(provider, store).execute(
        1, "1h", datetime(2026, 1, 1), datetime(2026, 1, 2), 500
    )

    assert provider.calls == [datetime(2026, 1, 1, 1)]
    assert len(response.candles) == 4


def test_no_fetch_when_storage_already_covers_range():
    store = FakeStore(
        [candle(datetime(2026, 1, 1, h)) for h in range(24)]
        + [candle(datetime(2026, 1, 2))]
    )
    provider = FakeProvider([])

    make_use_case(provider, store).execute(
        1, "1h", datetime(2026, 1, 1), datetime(2026, 1, 2), 500
    )

    assert provider.calls == []


def test_invalid_timeframe_is_rejected():
    with pytest.raises(AppError) as error:
        make_use_case(FakeProvider([]), FakeStore()).execute(
            1, "2w", datetime(2026, 1, 1), datetime(2026, 1, 2), 500
        )
    assert error.value.code == "invalid_timeframe"


def test_inverted_range_is_rejected():
    with pytest.raises(AppError) as error:
        make_use_case(FakeProvider([]), FakeStore()).execute(
            1, "1h", datetime(2026, 1, 2), datetime(2026, 1, 1), 500
        )
    assert error.value.code == "invalid_range"


def test_unknown_instrument_is_rejected():
    use_case = GetOhlcvUseCase(FakeInstruments([]), FakeProvider([]), FakeStore(), EventBus())
    with pytest.raises(NotFoundError):
        use_case.execute(99, "1h", datetime(2026, 1, 1), datetime(2026, 1, 2), 500)
