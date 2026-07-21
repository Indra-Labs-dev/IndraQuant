from datetime import datetime, timezone
from decimal import Decimal

from src.modules.market_data.domain.entities import Candle


def aggregate_candles(candles: list[Candle], bucket_seconds: int) -> list[Candle]:
    """Resamples fine-grained candles into larger buckets aligned on epoch
    multiples of bucket_seconds. The last bucket may be partial — callers
    relying on the read-through refetch get it corrected on the next pass.
    """
    buckets: dict[int, list[Candle]] = {}
    for candle in candles:
        epoch = int(candle.open_time.replace(tzinfo=timezone.utc).timestamp())
        buckets.setdefault(epoch - epoch % bucket_seconds, []).append(candle)

    aggregated = []
    for bucket_start in sorted(buckets):
        members = sorted(buckets[bucket_start], key=lambda c: c.open_time)
        aggregated.append(
            Candle(
                open_time=datetime.fromtimestamp(bucket_start, tz=timezone.utc).replace(
                    tzinfo=None
                ),
                open=members[0].open,
                high=max(c.high for c in members),
                low=min(c.low for c in members),
                close=members[-1].close,
                volume=sum((c.volume for c in members), Decimal(0)),
            )
        )
    return aggregated
