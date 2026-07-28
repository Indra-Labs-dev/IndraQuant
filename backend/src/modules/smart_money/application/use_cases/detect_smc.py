from datetime import datetime

from pydantic import BaseModel

from src.modules.smart_money.domain.structures import (
    SmcCandle,
    detect_breaker_blocks,
    detect_fair_value_gap,
    detect_liquidity_pools,
    detect_mitigation_blocks,
    detect_order_block,
    detect_premium_discount_zone,
    detect_structures,
    detect_volume_imbalance,
)
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

    async def execute(
        self,
        instrument_id: int,
        timeframe: str,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> SmcResponse:
        response = await self._ohlcv.execute(instrument_id, timeframe, start, end, limit)
        candles = [
            SmcCandle(open=c.open, high=c.high, low=c.low, close=c.close)
            for c in response.candles
        ]
        detections = sorted(
            [
                *detect_structures(candles),
                *detect_structures(candles, lookback=1, scale="internal"),
                *detect_fair_value_gap(candles),
                *detect_order_block(candles),
                *detect_breaker_blocks(candles),
                *detect_mitigation_blocks(candles),
                *detect_liquidity_pools(candles),
                *detect_premium_discount_zone(candles),
                *detect_volume_imbalance(candles),
            ],
            key=lambda d: d.index,
        )
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
