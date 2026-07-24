from pydantic import BaseModel


class PairCorrelation(BaseModel):
    instrument_a: int
    symbol_a: str
    instrument_b: int
    symbol_b: str
    pearson: float | None
    spearman: float | None
    rolling: float | None
    dynamic: float | None
    sample_size: int
    explanation: str


class CorrelationMatrixResponse(BaseModel):
    timeframe: str
    window: int
    instrument_ids: list[int]
    pairs: list[PairCorrelation]
    explanation: str
