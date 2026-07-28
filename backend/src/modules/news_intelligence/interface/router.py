from fastapi import APIRouter, Depends, Query

from src.composition_root import (
    get_analyze_sentiment_use_case,
    get_current_user,
    get_news_intelligence_use_case,
    get_news_price_correlation_use_case,
    get_news_use_case,
)
from src.modules.auth.application.dto import UserProfile
from src.modules.news_intelligence.application.dto import (
    NewsIntelligenceResponse,
    NewsPriceCorrelationResponse,
)
from src.modules.news_intelligence.application.use_cases.analyze_news_intelligence import (
    AnalyzeNewsIntelligenceUseCase,
)
from src.modules.news_intelligence.application.use_cases.get_news import (
    GetNewsUseCase,
    NewsResponse,
)
from src.modules.news_intelligence.application.use_cases.get_news_price_correlation import (
    GetNewsPriceCorrelationUseCase,
)
from src.modules.sentiment_analysis.application.use_cases.analyze_news import (
    AnalyzeNewsSentimentUseCase,
    SentimentResponse,
)

router = APIRouter(prefix="/news", tags=["news"])


@router.get("")
async def get_news(
    limit: int = Query(default=20, ge=1, le=50),
    _: UserProfile = Depends(get_current_user),
    use_case: GetNewsUseCase = Depends(get_news_use_case),
) -> NewsResponse:
    return await use_case.execute(limit)


@router.get("/sentiment")
async def get_sentiment(
    limit: int = Query(default=10, ge=1, le=20),
    _: UserProfile = Depends(get_current_user),
    use_case: AnalyzeNewsSentimentUseCase = Depends(get_analyze_sentiment_use_case),
) -> SentimentResponse:
    return await use_case.execute(limit)


@router.get("/intelligence")
async def get_news_intelligence(
    limit: int = Query(default=30, ge=5, le=90),
    _: UserProfile = Depends(get_current_user),
    use_case: AnalyzeNewsIntelligenceUseCase = Depends(get_news_intelligence_use_case),
) -> NewsIntelligenceResponse:
    return await use_case.execute(limit)


@router.get("/price-correlation/{instrument_id}")
async def get_news_price_correlation(
    instrument_id: int,
    days: int = Query(default=14, ge=5, le=60),
    _: UserProfile = Depends(get_current_user),
    use_case: GetNewsPriceCorrelationUseCase = Depends(get_news_price_correlation_use_case),
) -> NewsPriceCorrelationResponse:
    return await use_case.execute(instrument_id, days)
