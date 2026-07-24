from datetime import datetime

from pydantic import BaseModel


class IndicatorPoint(BaseModel):
    time: datetime
    value: float


class IndicatorsResponse(BaseModel):
    instrument_id: int
    timeframe: str
    series: dict[str, list[IndicatorPoint]]


class VolumeProfileBucketDto(BaseModel):
    price_low: float
    price_high: float
    volume: float


class VolumeProfileResponse(BaseModel):
    instrument_id: int
    timeframe: str
    buckets: list[VolumeProfileBucketDto]
    point_of_control: VolumeProfileBucketDto | None
    explanation: str
