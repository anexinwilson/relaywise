from upstash_redis import Redis

from app.config.settings import settings


redis_client = Redis(
    url=settings.UPSTASH_REDIS_REST_URL,
    token=settings.UPSTASH_REDIS_REST_TOKEN,
)