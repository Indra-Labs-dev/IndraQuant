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


class DirectionPrediction(BaseModel):
    instrument_id: int
    timeframe: str
    as_of: datetime
    horizon_candles: int
    prob_up: float
    prob_down: float
    models: list[ModelScore]
    test_accuracy: float
    baseline_accuracy: float
    training_rows: int
    top_features: list[FeatureContribution]
    explanation: str
