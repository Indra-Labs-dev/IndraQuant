from collections import defaultdict
from datetime import datetime, timedelta, timezone

from src.modules.news_intelligence.application.dto import NewsPriceCorrelationResponse
from src.modules.news_intelligence.domain.analysis import news_price_correlation
from src.modules.sentiment_analysis.application.use_cases.analyze_news import (
    AnalyzeNewsSentimentUseCase,
)
from src.modules.technical_analysis.application.ports import OhlcvProvider

_SENTIMENT_HEADLINE_LIMIT = 15


class GetNewsPriceCorrelationUseCase:
    """Corrélation News/Prix (docs/roadmap #14): same-day correlation
    between the average sentiment of recent general market headlines
    (`AnalyzeNewsSentimentUseCase`, already computed and cached) and an
    instrument's daily return over the same days — an honest,
    contemporaneous link, not a predictive signal, and explicitly noted
    as such since the headlines are market-wide, not instrument-specific."""

    def __init__(
        self, sentiment: AnalyzeNewsSentimentUseCase, ohlcv: OhlcvProvider
    ) -> None:
        self._sentiment = sentiment
        self._ohlcv = ohlcv

    async def execute(self, instrument_id: int, days: int = 14) -> NewsPriceCorrelationResponse:
        sentiment = await self._sentiment.execute(limit=_SENTIMENT_HEADLINE_LIMIT)

        daily_sentiment: dict = defaultdict(list)
        for item in sentiment.items:
            if item.published_at is None:
                continue
            daily_sentiment[item.published_at.date()].append(item.score)

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days + 2)
        response = await self._ohlcv.execute(instrument_id, "1d", start, end, 200)
        closes_by_day = {c.open_time.date(): c.close for c in response.candles}
        sorted_days = sorted(closes_by_day.keys())

        aligned_sentiment: list[float] = []
        aligned_returns: list[float] = []
        for i in range(1, len(sorted_days)):
            day = sorted_days[i]
            if day not in daily_sentiment:
                continue
            previous_close = closes_by_day[sorted_days[i - 1]]
            close = closes_by_day[day]
            if previous_close <= 0:
                continue
            aligned_sentiment.append(sum(daily_sentiment[day]) / len(daily_sentiment[day]))
            aligned_returns.append(close / previous_close - 1.0)

        correlation = news_price_correlation(aligned_sentiment, aligned_returns)

        return NewsPriceCorrelationResponse(
            instrument_id=instrument_id,
            days_analyzed=len(aligned_sentiment),
            correlation=round(correlation, 4) if correlation is not None else None,
            explanation=(
                f"Corrélation le même jour entre le sentiment moyen des actualités "
                f"générales et le rendement de l'instrument, sur "
                f"{len(aligned_sentiment)} jour(s) où les deux étaient disponibles : "
                + (f"{correlation:+.2f}." if correlation is not None else "historique insuffisant.")
                + " Les actualités analysées sont générales (marché), pas spécifiques à "
                "cet instrument — une corrélation faible est attendue et normale. "
                "Corrélation contemporaine, pas prédictive."
            ),
        )
