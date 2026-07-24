import json
from datetime import datetime, timezone

from pydantic import BaseModel

from src.modules.news_intelligence.infrastructure.rss_repository import (
    RssNewsRepository,
)
from src.shared.events.event_bus import EventBus, NewsReceived

_CACHE_TTL_SECONDS = 300


class NewsItem(BaseModel):
    source: str
    title: str
    link: str
    published_at: datetime | None


class NewsResponse(BaseModel):
    items: list[NewsItem]


class GetNewsUseCase:
    def __init__(
        self,
        repository: RssNewsRepository,
        cache=None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._repository = repository
        self._cache = cache
        self._event_bus = event_bus

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

        if self._event_bus is not None:
            self._event_bus.publish(
                NewsReceived(count=len(response.items), fetched_at=datetime.now(timezone.utc))
            )

        if self._cache is not None:
            try:
                self._cache.set(
                    cache_key, response.model_dump_json(), ex=_CACHE_TTL_SECONDS
                )
            except Exception:
                pass
        return response
