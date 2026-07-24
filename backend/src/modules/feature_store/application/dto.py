from datetime import datetime

from pydantic import BaseModel


class FeatureVectorResponse(BaseModel):
    instrument_id: int
    timeframe: str
    as_of: datetime
    price: float
    sma_20: float | None
    sma_50: float | None
    rsi_14: float | None
    macd_histogram: float | None
    bollinger_upper: float | None
    bollinger_lower: float | None
    volatility_20: float | None
    volatility_z_score: float | None
    volume_z_score: float | None
    return_1: float | None
