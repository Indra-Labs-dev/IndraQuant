from datetime import datetime

from pydantic import BaseModel

from src.modules.smart_money.domain.structures import SmcCandle, detect_structures
from src.modules.technical_analysis.application.ports import OhlcvProvider


class SmcDto(BaseModel):
    kind: str
    time: datetime
    direction: str
    confidence: float
    explanation: str


class SmcResponse(BaseModel):
    instrument_id: int
    timeframe: str
    detections: list[SmcDto]


class DetectSmcUseCase:
    def __init__(self, ohlcv: OhlcvProvider) -> None:
        self._ohlcv = ohlcv

    def execute(
        self,
        instrument_id: int,
        timeframe: str,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> SmcResponse:
        response = self._ohlcv.execute(instrument_id, timeframe, start, end, limit)
        candles = [
            SmcCandle(open=c.open, high=c.high, low=c.low, close=c.close)
            for c in response.candles
        ]
        detections = detect_structures(candles)
        return SmcResponse(
            instrument_id=instrument_id,
            timeframe=response.timeframe,
            detections=[
                SmcDto(
                    kind=d.kind,
                    time=response.candles[d.index].open_time,
                    direction=d.direction,
                    confidence=d.confidence,
                    explanation=d.explanation,
                )
                for d in detections
            ],
        )
