from datetime import datetime, timedelta, timezone

from src.modules.prediction_engine.infrastructure.sqlalchemy_repository import (
    SqlAlchemyPredictionRepository,
)
from src.modules.technical_analysis.application.ports import OhlcvProvider

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}


class ResolvePredictionsUseCase:
    """Checks pending predictions whose target candle has now fully closed,
    determines whether the model was right, and records the outcome — the
    factual basis the Prediction Engine uses to recalibrate itself (ADR-020)."""

    def __init__(
        self, repository: SqlAlchemyPredictionRepository, ohlcv: OhlcvProvider
    ) -> None:
        self._repository = repository
        self._ohlcv = ohlcv

    def execute(self) -> int:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        resolved = 0
        for prediction in self._repository.list_unresolved_ready(now):
            seconds = _TIMEFRAME_SECONDS.get(prediction.timeframe, 3_600)
            # Only trust the target candle's close once its own duration has
            # fully elapsed (not mid-formation).
            if now < prediction.target_time + timedelta(seconds=seconds):
                continue

            try:
                response = self._ohlcv.execute(
                    prediction.instrument_id,
                    prediction.timeframe,
                    prediction.as_of - timedelta(seconds=seconds),
                    prediction.target_time + timedelta(seconds=seconds),
                    10,
                )
            except Exception:
                continue

            as_of_candle = next(
                (
                    c
                    for c in response.candles
                    if c.open_time.replace(tzinfo=None) == prediction.as_of
                ),
                None,
            )
            target_candle = next(
                (
                    c
                    for c in response.candles
                    if c.open_time.replace(tzinfo=None) == prediction.target_time
                ),
                None,
            )
            if as_of_candle is None or target_candle is None:
                continue

            prediction.actual_direction = (
                "up" if target_candle.close > as_of_candle.close else "down"
            )
            prediction.correct = (
                prediction.actual_direction == prediction.predicted_direction
            )
            prediction.resolved_at = now
            resolved += 1
        return resolved
