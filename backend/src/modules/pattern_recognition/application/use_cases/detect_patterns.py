from datetime import datetime

from src.modules.pattern_recognition.application.dto import (
    PatternDto,
    PatternsResponse,
)
from src.modules.pattern_recognition.domain.patterns import (
    Ohlc,
    detect_double_top,
    detect_engulfing,
    detect_hammer,
)
from src.modules.technical_analysis.application.ports import OhlcvProvider


class DetectPatternsUseCase:
    def __init__(self, ohlcv: OhlcvProvider) -> None:
        self._ohlcv = ohlcv

    async def execute(
        self,
        instrument_id: int,
        timeframe: str,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> PatternsResponse:
        response = await self._ohlcv.execute(instrument_id, timeframe, start, end, limit)
        candles = [
            Ohlc(open=c.open, high=c.high, low=c.low, close=c.close)
            for c in response.candles
        ]
        detections = (
            detect_engulfing(candles)
            + detect_hammer(candles)
            + detect_double_top(candles)
        )
        detections.sort(key=lambda d: d.index)
        return PatternsResponse(
            instrument_id=instrument_id,
            timeframe=response.timeframe,
            patterns=[
                PatternDto(
                    pattern=d.pattern,
                    time=response.candles[d.index].open_time,
                    direction=d.direction,
                    confidence=d.confidence,
                    explanation=d.explanation,
                )
                for d in detections
            ],
        )
