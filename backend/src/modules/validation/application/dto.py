from pydantic import BaseModel


class FoldResultDto(BaseModel):
    fold: int
    train_size: int
    test_size: int
    accuracy: float | None


class CvSummaryDto(BaseModel):
    method: str
    folds: list[FoldResultDto]
    mean_accuracy: float | None
    std_accuracy: float | None
    explanation: str


class ModelValidationResponse(BaseModel):
    instrument_id: int
    timeframe: str
    naive_split_accuracy: float | None
    time_series_cv: CvSummaryDto
    purged_embargo_cv: CvSummaryDto
    nested_cv: CvSummaryDto
    explanation: str


class BootstrapDto(BaseModel):
    mean: float
    ci_low: float
    ci_high: float
    confidence: float
    explanation: str


class MonteCarloDto(BaseModel):
    observed_return: float
    p_value: float
    null_mean: float
    null_std: float
    explanation: str


class WhiteRealityCheckDto(BaseModel):
    best_candidate_index: int
    best_mean_return: float
    p_value: float
    n_candidates: int
    explanation: str


class BacktestValidationResponse(BaseModel):
    instrument_id: int
    timeframe: str
    bootstrap: BootstrapDto
    monte_carlo: MonteCarloDto
    reality_check: WhiteRealityCheckDto
    explanation: str
