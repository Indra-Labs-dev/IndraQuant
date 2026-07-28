from datetime import datetime

from src.modules.market_data.application.use_cases.get_ohlcv import GetOhlcvUseCase
from src.shared.events.event_bus import EventBus
from tests.unit.test_get_ohlcv import BTC, FakeInstruments, FakeProvider, FakeStore, candle


async def test_backfills_history_older_than_stored():
    store = FakeStore([candle(datetime(2026, 1, 3, h)) for h in range(3)])
    older = [candle(datetime(2026, 1, 1, h)) for h in range(24)]
    newer = [candle(datetime(2026, 1, 3, h)) for h in (2, 3)]
    provider = FakeProvider([older, newer])
    use_case = GetOhlcvUseCase(FakeInstruments([BTC]), provider, store, EventBus())

    response = await use_case.execute(
        1, "1h", datetime(2026, 1, 1), datetime(2026, 1, 4), 500
    )

    # First call backfills from the requested start, second resumes forward.
    assert provider.calls[0] == datetime(2026, 1, 1)
    assert provider.calls[1] == datetime(2026, 1, 3, 2)
    assert len(response.candles) == 24 + 4
