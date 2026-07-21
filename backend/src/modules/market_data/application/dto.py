from datetime import datetime

from pydantic import BaseModel


class InstrumentDto(BaseModel):
    id: int
    symbol: str
    exchange: str
    asset_class: str


class InstrumentsResponse(BaseModel):
    instruments: list[InstrumentDto]


class CandleDto(BaseModel):
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class OhlcvResponse(BaseModel):
    instrument_id: int
    timeframe: str
    candles: list[CandleDto]
