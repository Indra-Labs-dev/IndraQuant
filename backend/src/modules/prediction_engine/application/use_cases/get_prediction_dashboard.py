from datetime import datetime, timezone

from pydantic import BaseModel

from src.modules.machine_learning.domain.calibration import BUCKET_WIDTH
from src.modules.machine_learning.domain.trend import rolling_accuracy_trend
from src.modules.market_data.domain.repositories import InstrumentRepository
from src.modules.prediction_engine.infrastructure.sqlalchemy_repository import (
    SqlAlchemyPredictionRepository,
)

_TREND_WINDOW = 20


class PredictionRecord(BaseModel):
    id: int
    instrument_id: int
    symbol: str
    timeframe: str
    as_of: datetime
    target_time: datetime
    predicted_direction: str
    raw_prob_up: float
    actual_direction: str | None
    correct: bool | None
    resolved_at: datetime | None


class CalibrationBucket(BaseModel):
    low: float
    high: float
    n: int
    accuracy: float | None


class AccuracyTrendPoint(BaseModel):
    index: int
    resolved_at: datetime
    rolling_accuracy: float
    sample_size: int


class TimeframeSummary(BaseModel):
    timeframe: str
    resolved: int
    pending: int
    accuracy: float | None


class PredictionDashboard(BaseModel):
    timeframe: str
    summary: list[TimeframeSummary]
    calibration: list[CalibrationBucket]
    accuracy_trend: list[AccuracyTrendPoint]
    recent: list[PredictionRecord]


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class GetPredictionDashboardUseCase:
    """Read-side view over the Prediction Engine's real, verified track
    record (ADR-020/ADR-023) — no fabricated data, only what has actually
    been predicted and resolved."""

    def __init__(
        self,
        predictions: SqlAlchemyPredictionRepository,
        instruments: InstrumentRepository,
    ) -> None:
        self._predictions = predictions
        self._instruments = instruments

    def execute(
        self, timeframe: str, instrument_id: int | None, limit: int
    ) -> PredictionDashboard:
        summary = [
            TimeframeSummary(**row) for row in self._predictions.summary_by_timeframe()
        ]

        calibration: list[CalibrationBucket] = []
        low = 0.5
        while low < 1.0 - 1e-9:
            high = round(low + BUCKET_WIDTH, 4)
            n, accuracy = self._predictions.calibration_stats(timeframe, low, high)
            calibration.append(CalibrationBucket(low=low, high=high, n=n, accuracy=accuracy))
            low = high

        resolved_rows = self._predictions.list_resolved_ordered(instrument_id, timeframe)
        trend_values = rolling_accuracy_trend([bool(r.correct) for r in resolved_rows])
        accuracy_trend = [
            AccuracyTrendPoint(
                index=i + 1,
                resolved_at=_utc(row.resolved_at),
                rolling_accuracy=value,
                sample_size=min(i + 1, _TREND_WINDOW),
            )
            for i, (row, value) in enumerate(zip(resolved_rows, trend_values))
        ]

        symbols = {i.id: i.symbol for i in self._instruments.list_instruments()}
        recent = [
            PredictionRecord(
                id=r.id,
                instrument_id=r.instrument_id,
                symbol=symbols.get(r.instrument_id, f"#{r.instrument_id}"),
                timeframe=r.timeframe,
                as_of=_utc(r.as_of),
                target_time=_utc(r.target_time),
                predicted_direction=r.predicted_direction,
                raw_prob_up=float(r.raw_prob_up),
                actual_direction=r.actual_direction,
                correct=r.correct,
                resolved_at=_utc(r.resolved_at) if r.resolved_at else None,
            )
            for r in self._predictions.list_recent(instrument_id, timeframe, limit)
        ]

        return PredictionDashboard(
            timeframe=timeframe,
            summary=summary,
            calibration=calibration,
            accuracy_trend=accuracy_trend,
            recent=recent,
        )
