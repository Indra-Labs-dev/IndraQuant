from datetime import datetime

from pydantic import BaseModel


class IndicatorPoint(BaseModel):
    time: datetime
    value: float


class IndicatorsResponse(BaseModel):
    instrument_id: int
    timeframe: str
    series: dict[str, list[IndicatorPoint]]
