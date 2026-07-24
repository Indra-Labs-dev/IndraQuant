from pydantic import BaseModel


class MarketRegimeResponse(BaseModel):
    instrument_id: int
    timeframe: str
    trend: str
    volatility: str
    is_trending: bool
    is_panic: bool
    confidence: float
    label: str
    explanation: str
