from datetime import datetime

from pydantic import BaseModel, Field

Method = str  # "grid" | "random" | "bayesian_optuna" | "bayesian_hyperopt"


class HpoTrialDto(BaseModel):
    trial: int
    params: dict[str, float]
    value: float | None


class HpoResultDto(BaseModel):
    method: str
    best_params: dict[str, float]
    best_value: float | None
    n_trials: int
    trials: list[HpoTrialDto]
    explanation: str


class OptimizeStrategyRequest(BaseModel):
    instrument_id: int
    timeframe: str
    from_: datetime = Field(alias="from")
    to: datetime
    strategy_type: str = "sma_crossover"
    method: Method = "bayesian_optuna"
    n_trials: int = Field(default=30, ge=5, le=200)
    initial_capital: float = Field(default=10_000.0, gt=0)


class OptimizeModelRequest(BaseModel):
    instrument_id: int
    timeframe: str
    method: Method = "bayesian_optuna"
    n_trials: int = Field(default=20, ge=5, le=100)
