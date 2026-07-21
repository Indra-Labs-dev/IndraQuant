import json
from datetime import datetime

from pydantic import BaseModel

from src.modules.news_intelligence.infrastructure.rss_repository import (
    RssNewsRepository,
)

_CACHE_TTL_SECONDS = 300


class NewsItem(BaseModel):
    source: str
    title: str
    link: str
    published_at: datetime | None


class NewsResponse(BaseModel):
    items: list[NewsItem]


class GetNewsUseCase:
    def __init__(self, repository: RssNewsRepository, cache=None) -> None:
        self._repository = repository
        self._cache = cache

    def execute(self, limit: int = 20) -> NewsResponse:
        cache_key = f"news:headlines:{limit}"
        if self._cache is not None:
            try:
                cached = self._cache.get(cache_key)
                if cached:
                    return NewsResponse(**json.loads(cached))
            except Exception:
                pass

        items = self._repository.fetch_headlines()[:limit]
        response = NewsResponse(items=[NewsItem(**item) for item in items])

        if self._cache is not None:
            try:
                self._cache.set(
                    cache_key, response.model_dump_json(), ex=_CACHE_TTL_SECONDS
                )
            except Exception:
                pass
        return response
