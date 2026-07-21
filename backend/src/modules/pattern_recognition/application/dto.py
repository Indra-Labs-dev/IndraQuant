from datetime import datetime

from pydantic import BaseModel


class PatternDto(BaseModel):
    pattern: str
    time: datetime
    direction: str
    confidence: float
    explanation: str


class PatternsResponse(BaseModel):
    instrument_id: int
    timeframe: str
    patterns: list[PatternDto]
