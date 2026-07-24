from pydantic import BaseModel


class EngineSignalDto(BaseModel):
    engine: str
    direction: str
    score: float
    confidence: float
    explanation: str


class RegimeSummary(BaseModel):
    trend: str
    volatility: str
    is_trending: bool
    is_panic: bool
    label: str


class MetaDecisionResponse(BaseModel):
    instrument_id: int
    timeframe: str
    direction: str
    score: float
    confidence: float
    engines: list[EngineSignalDto]
    regime: RegimeSummary | None
    explanation: str
