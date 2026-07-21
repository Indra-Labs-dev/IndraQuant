from datetime import datetime
from decimal import Decimal

from src.modules.market_data.domain.aggregation import aggregate_candles
from src.modules.market_data.domain.entities import Candle


def candle(second: int, o: str, h: str, l: str, c: str, v: str) -> Candle:
    return Candle(
        open_time=datetime(2026, 1, 1, 0, 0, second),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(l),
        close=Decimal(c),
        volume=Decimal(v),
    )


def test_aggregates_1s_candles_into_aligned_5s_buckets():
    fine = [
        candle(0, "10", "12", "9", "11", "1"),
        candle(1, "11", "15", "11", "14", "2"),
        candle(4, "14", "14", "8", "9", "1"),
        candle(5, "9", "10", "9", "10", "3"),
    ]

    result = aggregate_candles(fine, 5)

    assert len(result) == 2
    first, second = result
    assert first.open_time == datetime(2026, 1, 1, 0, 0, 0)
    assert (first.open, first.high, first.low, first.close, first.volume) == (
        Decimal("10"),
        Decimal("15"),
        Decimal("8"),
        Decimal("9"),
        Decimal("4"),
    )
    assert second.open_time == datetime(2026, 1, 1, 0, 0, 5)
    assert second.volume == Decimal("3")


def test_empty_input_returns_empty_list():
    assert aggregate_candles([], 30) == []
