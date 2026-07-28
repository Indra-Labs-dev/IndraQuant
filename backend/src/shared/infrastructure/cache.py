from redis.asyncio import Redis

from src.shared.infrastructure.config import settings

redis_client = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
