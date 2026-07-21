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


class FakeRepository:
    def __init__(self, rows: list[FakePredictionRow]) -> None:
        self.rows = rows

    def list_unresolved_ready(self, now, limit=200):
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

    def execute(self, instrument_id, timeframe, start, end, limit):
        return FakeOhlcvResponse(
            candles=[c for c in self.candles if start <= c.open_time <= end]
        )


def test_resolves_prediction_once_target_candle_has_closed():
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

    resolved = use_case.execute()

    assert resolved == 1
    assert prediction.actual_direction == "up"
    assert prediction.correct is True
    assert prediction.resolved_at is not None


def test_marks_incorrect_when_prediction_was_wrong():
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

    use_case.execute()

    assert prediction.actual_direction == "down"
    assert prediction.correct is False


def test_skips_candles_missing_from_provider():
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

    resolved = use_case.execute()

    assert resolved == 0
    assert prediction.resolved_at is None
