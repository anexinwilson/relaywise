from concurrent.futures import ThreadPoolExecutor
from composio import Composio
from upstash_redis import Redis
from config import settings

_composio_client = None
_redis_client = None
_executor = ThreadPoolExecutor(max_workers=4)

def get_composio_client():
    global _composio_client
    if _composio_client is None:
        _composio_client = Composio(api_key=settings.COMPOSIO_API_KEY)
    return _composio_client

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis(
            url=settings.UPSTASH_REDIS_REST_URL,
            token=settings.UPSTASH_REDIS_REST_TOKEN,
        )
    return _redis_client

def get_executor():
    return _executor
