from pydantic import BaseModel


class ConfidenceFactorDto(BaseModel):
    name: str
    multiplier: float
    explanation: str


class GlobalConfidenceResponse(BaseModel):
    instrument_id: int
    timeframe: str
    direction: str
    score: float
    level: str
    base_confidence: float
    factors: list[ConfidenceFactorDto]
    explanation: str
