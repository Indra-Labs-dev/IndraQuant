from datetime import datetime, timezone
from time import mktime

_FEEDS = (
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
)


class RssNewsRepository:
    def fetch_headlines(self, limit_per_feed: int = 10) -> list[dict]:
        import feedparser

        items: list[dict] = []
        for source, url in _FEEDS:
            try:
                feed = feedparser.parse(url)
            except Exception:
                continue
            for entry in feed.entries[:limit_per_feed]:
                published = None
                parsed = getattr(entry, "published_parsed", None) or getattr(
                    entry, "updated_parsed", None
                )
                if parsed:
                    published = datetime.fromtimestamp(
                        mktime(parsed), tz=timezone.utc
                    ).replace(tzinfo=None)
                items.append(
                    {
                        "source": source,
                        "title": getattr(entry, "title", "").strip(),
                        "link": getattr(entry, "link", ""),
                        "published_at": published,
                    }
                )
        items.sort(
            key=lambda i: i["published_at"] or datetime.min, reverse=True
        )
        return items
