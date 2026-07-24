from datetime import datetime

from pydantic import BaseModel


class ModelVersionDto(BaseModel):
    version: int
    as_of: datetime
    champion_model_type: str
    xgboost_accuracy: float
    logistic_regression_accuracy: float
    ensemble_accuracy: float
    baseline_accuracy: float
    training_rows: int
    is_champion: bool
    rolled_back: bool


class ModelRegistryResponse(BaseModel):
    instrument_id: int
    timeframe: str
    versions: list[ModelVersionDto]
    explanation: str


class RollbackResponse(BaseModel):
    instrument_id: int
    timeframe: str
    champion_version: int
    explanation: str


class AbTestResponse(BaseModel):
    instrument_id: int
    timeframe: str
    winner: str
    xgboost_edge_mean: float
    xgboost_edge_ci_low: float
    xgboost_edge_ci_high: float
    logistic_regression_edge_mean: float
    logistic_regression_edge_ci_low: float
    logistic_regression_edge_ci_high: float
    sample_size: int
    explanation: str
