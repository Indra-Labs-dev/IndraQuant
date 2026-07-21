from fastapi import APIRouter, Depends, Query

from src.composition_root import (
    get_analyze_sentiment_use_case,
    get_current_user,
    get_news_use_case,
)
from src.modules.auth.application.dto import UserProfile
from src.modules.news_intelligence.application.use_cases.get_news import (
    GetNewsUseCase,
    NewsResponse,
)
from src.modules.sentiment_analysis.application.use_cases.analyze_news import (
    AnalyzeNewsSentimentUseCase,
    SentimentResponse,
)

router = APIRouter(prefix="/news", tags=["news"])


@router.get("")
def get_news(
    limit: int = Query(default=20, ge=1, le=50),
    _: UserProfile = Depends(get_current_user),
    use_case: GetNewsUseCase = Depends(get_news_use_case),
) -> NewsResponse:
    return use_case.execute(limit)


@router.get("/sentiment")
def get_sentiment(
    limit: int = Query(default=10, ge=1, le=20),
    _: UserProfile = Depends(get_current_user),
    use_case: AnalyzeNewsSentimentUseCase = Depends(get_analyze_sentiment_use_case),
) -> SentimentResponse:
    return use_case.execute(limit)
