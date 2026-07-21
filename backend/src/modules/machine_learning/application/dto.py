from datetime import datetime

from pydantic import BaseModel


class FeatureContribution(BaseModel):
    feature: str
    value: float
    contribution: float


class ModelScore(BaseModel):
    name: str
    prob_up: float
    test_accuracy: float


class PredictionTrackRecord(BaseModel):
    """Real, verified track record for predictions in this confidence
    bucket/timeframe — the factual basis for self-correction (ADR-020)."""

    bucket_low: float
    bucket_high: float
    bucket_resolved: int
    bucket_accuracy: float | None
    overall_resolved: int
    overall_accuracy: float | None


class DirectionPrediction(BaseModel):
    instrument_id: int
    timeframe: str
    as_of: datetime
    horizon_candles: int
    prob_up: float
    prob_down: float
    raw_prob_up: float
    models: list[ModelScore]
    test_accuracy: float
    baseline_accuracy: float
    training_rows: int
    top_features: list[FeatureContribution]
    track_record: PredictionTrackRecord
    explanation: str
