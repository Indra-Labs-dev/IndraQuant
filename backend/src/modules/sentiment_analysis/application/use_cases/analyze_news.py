import json
from datetime import datetime

from pydantic import BaseModel

from src.modules.news_intelligence.application.use_cases.get_news import (
    GetNewsUseCase,
)
from src.modules.sentiment_analysis.infrastructure.ollama_client import OllamaClient
from src.shared.kernel.errors import AppError

_CACHE_TTL_SECONDS = 600


class HeadlineSentiment(BaseModel):
    source: str
    title: str
    link: str
    published_at: datetime | None
    sentiment: str
    score: float
    rationale: str


class SentimentResponse(BaseModel):
    items: list[HeadlineSentiment]
    average_score: float
    model: str
    explanation: str


class AnalyzeNewsSentimentUseCase:
    def __init__(
        self, news: GetNewsUseCase, ollama: OllamaClient, cache=None
    ) -> None:
        self._news = news
        self._ollama = ollama
        self._cache = cache

    def execute(self, limit: int = 10) -> SentimentResponse:
        cache_key = f"sentiment:news:{limit}"
        if self._cache is not None:
            try:
                cached = self._cache.get(cache_key)
                if cached:
                    return SentimentResponse(**json.loads(cached))
            except Exception:
                pass

        news = self._news.execute(limit).items
        if not news:
            raise AppError("no_news", "Aucune actualité récupérée.", 502)

        try:
            classified = self._ollama.classify_headlines([n.title for n in news])
        except Exception as error:
            raise AppError(
                "sentiment_unavailable",
                f"Analyse de sentiment indisponible (Ollama) : {error}",
                http_status=502,
            )

        items = [
            HeadlineSentiment(
                source=n.source,
                title=n.title,
                link=n.link,
                published_at=n.published_at,
                sentiment=c["sentiment"],
                score=max(min(c["score"], 1.0), -1.0),
                rationale=c["rationale"],
            )
            for n, c in zip(news, classified)
        ]
        average = sum(i.score for i in items) / len(items)
        tone = (
            "plutôt positif"
            if average > 0.15
            else "plutôt négatif" if average < -0.15 else "neutre"
        )
        response = SentimentResponse(
            items=items,
            average_score=round(average, 3),
            model="llama3.1:8b (Ollama, local)",
            explanation=(
                f"Sentiment agrégé {tone} (score moyen {average:+.2f} sur "
                f"{len(items)} titres). Chaque titre est classé par un modèle "
                "de langage local avec justification — estimation qualitative, "
                "pas un signal de trading."
            ),
        )

        if self._cache is not None:
            try:
                self._cache.set(
                    cache_key, response.model_dump_json(), ex=_CACHE_TTL_SECONDS
                )
            except Exception:
                pass
        return response
