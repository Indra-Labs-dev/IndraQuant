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


class PriceIntervalTrackRecord(BaseModel):
    """Real, verified coverage of past price-interval estimates for this
    timeframe — how often the actual outcome fell inside the declared
    interval, the factual basis used to widen/narrow future intervals
    (ADR-029)."""

    resolved: int
    empirical_coverage: float | None
    declared_confidence: float


class PriceTargetEstimate(BaseModel):
    """Probabilistic price projection (ADR-025) — never a single number:
    an expected price plus a low/high interval at a stated confidence,
    grounded in the regressor's own historical error on held-out data."""

    current_price: float
    expected_price: float
    low_price: float
    high_price: float
    confidence: float
    test_error_pct: float
    track_record: PriceIntervalTrackRecord
    explanation: str


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
    price_target: PriceTargetEstimate
    explanation: str
