from datetime import datetime

from src.modules.market_data.application.use_cases.get_ohlcv import GetOhlcvUseCase
from src.shared.events.event_bus import EventBus
from tests.unit.test_get_ohlcv import BTC, FakeInstruments, FakeProvider, FakeStore, candle


class FakeCooldownCache:
    """Mimics Redis SET key value NX EX seconds: returns True only the
    first time a key is set, False on every call while it's still "alive"."""

    def __init__(self) -> None:
        self._keys: set[str] = set()

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self._keys:
            return False
        self._keys.add(key)
        return True


def test_second_call_within_cooldown_skips_provider_fetch():
    store = FakeStore([candle(datetime(2026, 1, 1, 0))])
    provider = FakeProvider(
        [[candle(datetime(2026, 1, 1, h)) for h in (0, 1)]]
        + [[candle(datetime(2026, 1, 1, h)) for h in (0, 1)]]
    )
    cache = FakeCooldownCache()
    use_case = GetOhlcvUseCase(
        FakeInstruments([BTC]), provider, store, EventBus(), cache=cache
    )

    use_case.execute(1, "1h", datetime(2026, 1, 1), datetime(2026, 1, 2), 500)
    assert len(provider.calls) == 1

    use_case.execute(1, "1h", datetime(2026, 1, 1), datetime(2026, 1, 2), 500)
    assert len(provider.calls) == 1


def test_cooldown_is_scoped_per_instrument_and_timeframe():
    store_a = FakeStore([candle(datetime(2026, 1, 1, 0))])
    store_b = FakeStore([candle(datetime(2026, 1, 1, 0))])
    provider_a = FakeProvider([[candle(datetime(2026, 1, 1, h)) for h in (0, 1)]])
    provider_b = FakeProvider([[candle(datetime(2026, 1, 1, h)) for h in (0, 1)]])
    cache = FakeCooldownCache()

    GetOhlcvUseCase(FakeInstruments([BTC]), provider_a, store_a, EventBus(), cache=cache).execute(
        1, "1h", datetime(2026, 1, 1), datetime(2026, 1, 2), 500
    )
    GetOhlcvUseCase(FakeInstruments([BTC]), provider_b, store_b, EventBus(), cache=cache).execute(
        1, "5m", datetime(2026, 1, 1), datetime(2026, 1, 2), 500
    )

    assert len(provider_a.calls) == 1
    assert len(provider_b.calls) == 1


def test_no_cache_never_debounces():
    store = FakeStore([candle(datetime(2026, 1, 1, 0))])
    provider = FakeProvider(
        [[candle(datetime(2026, 1, 1, h)) for h in (0, 1)]]
        + [[candle(datetime(2026, 1, 1, h)) for h in (0, 1)]]
    )
    use_case = GetOhlcvUseCase(FakeInstruments([BTC]), provider, store, EventBus())

    use_case.execute(1, "1h", datetime(2026, 1, 1), datetime(2026, 1, 2), 500)
    use_case.execute(1, "1h", datetime(2026, 1, 1), datetime(2026, 1, 2), 500)
    assert len(provider.calls) == 2
