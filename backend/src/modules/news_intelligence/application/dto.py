from datetime import datetime

from pydantic import BaseModel


class NewsClusterDto(BaseModel):
    summary: str
    sources: list[str]
    headline_count: int
    category: str
    is_event: bool
    event_type: str
    impact: str
    credibility_score: float
    credibility_level: str
    latest_published_at: datetime | None
    titles: list[str]


class NewsIntelligenceResponse(BaseModel):
    clusters: list[NewsClusterDto]
    explanation: str


class NewsPriceCorrelationResponse(BaseModel):
    instrument_id: int
    days_analyzed: int
    correlation: float | None
    explanation: str
