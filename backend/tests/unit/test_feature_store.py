from datetime import datetime, timezone

from src.modules.feature_store.application.service import FeatureStoreService

_AS_OF = datetime(2026, 1, 1, tzinfo=timezone.utc)


class FakeCache:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.gets = 0
        self.sets = 0

    def get(self, key: str):
        self.gets += 1
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.sets += 1
        self.store[key] = value


def _series(n: int = 80) -> tuple[list[float], list[float]]:
    closes = [100.0 + i * 0.5 for i in range(n)]
    volumes = [1_000.0 + i for i in range(n)]
    return closes, volumes


def test_compute_returns_expected_fields():
    closes, volumes = _series()
    service = FeatureStoreService(cache=None)
    vector = service.get_latest(1, "1h", _AS_OF, closes, volumes)

    assert vector.instrument_id == 1
    assert vector.timeframe == "1h"
    assert vector.price == closes[-1]
    assert vector.sma_20 is not None
    assert vector.sma_50 is not None
    assert vector.rsi_14 is not None
    assert vector.macd_histogram is not None


def test_returns_none_fields_with_insufficient_history():
    closes = [100.0, 101.0, 102.0]
    volumes = [1_000.0, 1_001.0, 1_002.0]
    service = FeatureStoreService(cache=None)
    vector = service.get_latest(1, "1h", _AS_OF, closes, volumes)

    assert vector.sma_20 is None
    assert vector.sma_50 is None
    assert vector.volatility_z_score is None


def test_cache_hit_skips_recomputation():
    closes, volumes = _series()
    cache = FakeCache()
    service = FeatureStoreService(cache=cache)

    first = service.get_latest(1, "1h", _AS_OF, closes, volumes)
    assert cache.sets == 1

    # Second call with different (wrong) series but the same cache key
    # (same instrument/timeframe/as_of) must return the cached vector
    # unchanged — proving the store, not the raw series, is the source of
    # truth once cached (docs/roadmap #5: avoid recomputation).
    second = service.get_latest(1, "1h", _AS_OF, [1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
    assert second == first
    assert cache.sets == 1


def test_different_as_of_misses_cache():
    closes, volumes = _series()
    cache = FakeCache()
    service = FeatureStoreService(cache=cache)

    service.get_latest(1, "1h", _AS_OF, closes, volumes)
    later = datetime(2026, 1, 1, 1, tzinfo=timezone.utc)
    service.get_latest(1, "1h", later, closes, volumes)

    assert cache.sets == 2
