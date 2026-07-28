import json

from src.modules.news_intelligence.application.dto import (
    NewsClusterDto,
    NewsIntelligenceResponse,
)
from src.modules.news_intelligence.application.use_cases.get_news import GetNewsUseCase
from src.modules.news_intelligence.domain.analysis import (
    cluster_headlines,
    credibility_score,
)
from src.modules.sentiment_analysis.infrastructure.ollama_client import OllamaClient
from src.shared.kernel.errors import AppError

_CACHE_TTL_SECONDS = 600


class AnalyzeNewsIntelligenceUseCase:
    """News Intelligence (docs/roadmap #14): groups the raw RSS headlines
    (`GetNewsUseCase`) into distinct stories via LLM-free clustering, then
    classifies each story (category, dated event or not, estimated
    impact), generates a one-sentence multi-source summary, and attaches
    a source-credibility score — all in addition to, not replacing, the
    existing per-headline sentiment analysis."""

    def __init__(self, news: GetNewsUseCase, ollama: OllamaClient, cache=None) -> None:
        self._news = news
        self._ollama = ollama
        self._cache = cache

    async def execute(self, limit: int = 30) -> NewsIntelligenceResponse:
        cache_key = f"news_intelligence:{limit}"
        if self._cache is not None:
            try:
                cached = await self._cache.get(cache_key)
                if cached:
                    return NewsIntelligenceResponse(**json.loads(cached))
            except Exception:
                pass

        news_response = await self._news.execute(limit)
        news = news_response.items
        if not news:
            raise AppError("no_news", "Aucune actualité récupérée.", 502)

        titles = [n.title for n in news]
        clusters_idx = cluster_headlines(titles)

        try:
            classifications = self._ollama.classify_news_intelligence(
                [titles[cluster[0]] for cluster in clusters_idx]
            )
        except Exception as error:
            raise AppError(
                "news_intelligence_unavailable",
                f"Analyse indisponible (Ollama) : {error}",
                502,
            )

        clusters: list[NewsClusterDto] = []
        for cluster, classification in zip(clusters_idx, classifications):
            member_titles = [titles[i] for i in cluster]
            member_sources = sorted({news[i].source for i in cluster})
            summary = self._ollama.summarize_cluster(member_titles)
            published_dates = [
                news[i].published_at for i in cluster if news[i].published_at is not None
            ]
            latest = max(published_dates) if published_dates else None

            credibilities = [credibility_score(s) for s in member_sources]
            avg_credibility = sum(c.score for c in credibilities) / len(credibilities)
            level = (
                "élevée" if avg_credibility >= 0.75
                else "moyenne" if avg_credibility >= 0.5
                else "faible"
            )

            clusters.append(
                NewsClusterDto(
                    summary=summary,
                    sources=member_sources,
                    headline_count=len(cluster),
                    category=classification["category"],
                    is_event=classification["is_event"],
                    event_type=classification["event_type"],
                    impact=classification["impact"],
                    credibility_score=round(avg_credibility, 2),
                    credibility_level=level,
                    latest_published_at=latest,
                    titles=member_titles,
                )
            )

        clusters.sort(key=lambda c: c.headline_count, reverse=True)
        multi_source = sum(1 for c in clusters if c.headline_count > 1)
        events = sum(1 for c in clusters if c.is_event)

        response = NewsIntelligenceResponse(
            clusters=clusters,
            explanation=(
                f"{len(news)} titre(s) regroupé(s) en {len(clusters)} sujet(s) distinct(s) "
                f"({multi_source} confirmé(s) par plusieurs sources), dont {events} "
                "événement(s) daté(s) identifié(s). Classification et estimation "
                "d'impact par modèle de langage local (Ollama) — qualitatif, jamais un "
                "signal de trading direct."
            ),
        )

        if self._cache is not None:
            try:
                await self._cache.set(cache_key, response.model_dump_json(), ex=_CACHE_TTL_SECONDS)
            except Exception:
                pass
        return response
