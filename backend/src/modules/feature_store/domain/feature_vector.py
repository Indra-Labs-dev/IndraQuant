"""Feature Store (docs/roadmap #5): the point-in-time technical feature
vector for one instrument/timeframe/candle. This is the single, named
representation every consumer (Meta Decision Engine's technical engines,
the `/features` endpoint) reads instead of independently recomputing
SMA/RSI/MACD/Bollinger/volatility from raw prices.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FeatureVector:
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
