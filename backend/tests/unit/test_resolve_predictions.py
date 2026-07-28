from dataclasses import dataclass, field
from datetime import datetime, timedelta

from src.modules.prediction_engine.application.use_cases.resolve_predictions import (
    ResolvePredictionsUseCase,
)


@dataclass
class FakePredictionRow:
    instrument_id: int
    timeframe: str
    as_of: datetime
    target_time: datetime
    predicted_direction: str
    actual_direction: str | None = None
    correct: bool | None = None
    resolved_at: datetime | None = None
    predicted_low_return: float | None = None
    predicted_high_return: float | None = None
    actual_return: float | None = None
    price_in_interval: bool | None = None


class FakeRepository:
    def __init__(self, rows: list[FakePredictionRow]) -> None:
        self.rows = rows

    async def list_unresolved_ready(self, now, limit=200):
        return [r for r in self.rows if r.resolved_at is None and r.target_time <= now]


@dataclass
class FakeCandle:
    open_time: datetime
    close: float


@dataclass
class FakeOhlcvResponse:
    candles: list


class FakeOhlcvProvider:
    def __init__(self, candles: list[FakeCandle]) -> None:
        self.candles = candles

    async def execute(self, instrument_id, timeframe, start, end, limit):
        return FakeOhlcvResponse(
            candles=[c for c in self.candles if start <= c.open_time <= end]
        )


async def test_resolves_prediction_once_target_candle_has_closed():
    as_of = datetime(2026, 1, 1, 0, 0)
    target = datetime(2026, 1, 1, 1, 0)
    prediction = FakePredictionRow(
        instrument_id=1,
        timeframe="1h",
        as_of=as_of,
        target_time=target,
        predicted_direction="up",
    )
    provider = FakeOhlcvProvider(
        [FakeCandle(as_of, 100.0), FakeCandle(target, 110.0)]
    )
    use_case = ResolvePredictionsUseCase(FakeRepository([prediction]), provider)

    resolved = await use_case.execute()

    assert resolved == 1
    assert prediction.actual_direction == "up"
    assert prediction.correct is True
    assert prediction.resolved_at is not None


async def test_marks_incorrect_when_prediction_was_wrong():
    as_of = datetime(2026, 1, 1, 0, 0)
    target = datetime(2026, 1, 1, 1, 0)
    prediction = FakePredictionRow(
        instrument_id=1,
        timeframe="1h",
        as_of=as_of,
        target_time=target,
        predicted_direction="up",
    )
    provider = FakeOhlcvProvider([FakeCandle(as_of, 100.0), FakeCandle(target, 90.0)])
    use_case = ResolvePredictionsUseCase(FakeRepository([prediction]), provider)

    await use_case.execute()

    assert prediction.actual_direction == "down"
    assert prediction.correct is False


async def test_skips_candles_missing_from_provider():
    as_of = datetime(2026, 1, 1, 0, 0)
    target = datetime(2026, 1, 1, 1, 0)
    prediction = FakePredictionRow(
        instrument_id=1,
        timeframe="1h",
        as_of=as_of,
        target_time=target,
        predicted_direction="up",
    )
    provider = FakeOhlcvProvider([])
    use_case = ResolvePredictionsUseCase(FakeRepository([prediction]), provider)

    resolved = await use_case.execute()

    assert resolved == 0
    assert prediction.resolved_at is None


async def test_marks_price_in_interval_when_actual_return_falls_inside():
    as_of = datetime(2026, 1, 1, 0, 0)
    target = datetime(2026, 1, 1, 1, 0)
    prediction = FakePredictionRow(
        instrument_id=1,
        timeframe="1h",
        as_of=as_of,
        target_time=target,
        predicted_direction="up",
        predicted_low_return=-0.05,
        predicted_high_return=0.05,
    )
    # actual return = ln(105/100) ≈ 0.0488, inside [-0.05, 0.05]
    provider = FakeOhlcvProvider([FakeCandle(as_of, 100.0), FakeCandle(target, 105.0)])
    use_case = ResolvePredictionsUseCase(FakeRepository([prediction]), provider)

    await use_case.execute()

    assert prediction.actual_return is not None
    assert prediction.price_in_interval is True


async def test_marks_price_outside_interval_when_actual_return_exceeds_it():
    as_of = datetime(2026, 1, 1, 0, 0)
    target = datetime(2026, 1, 1, 1, 0)
    prediction = FakePredictionRow(
        instrument_id=1,
        timeframe="1h",
        as_of=as_of,
        target_time=target,
        predicted_direction="up",
        predicted_low_return=-0.01,
        predicted_high_return=0.01,
    )
    # actual return = ln(150/100) ≈ 0.405, well outside [-0.01, 0.01]
    provider = FakeOhlcvProvider([FakeCandle(as_of, 100.0), FakeCandle(target, 150.0)])
    use_case = ResolvePredictionsUseCase(FakeRepository([prediction]), provider)

    await use_case.execute()

    assert prediction.price_in_interval is False


async def test_leaves_price_fields_untouched_when_no_price_prediction_was_stored():
    as_of = datetime(2026, 1, 1, 0, 0)
    target = datetime(2026, 1, 1, 1, 0)
    prediction = FakePredictionRow(
        instrument_id=1,
        timeframe="1h",
        as_of=as_of,
        target_time=target,
        predicted_direction="up",
    )
    provider = FakeOhlcvProvider([FakeCandle(as_of, 100.0), FakeCandle(target, 110.0)])
    use_case = ResolvePredictionsUseCase(FakeRepository([prediction]), provider)

    await use_case.execute()

    assert prediction.actual_return is None
    assert prediction.price_in_interval is None
