"""Upstash Redis client.

Built on first use rather than at import time so tests and local tooling can
import the module without credentials.
"""

from __future__ import annotations

from functools import lru_cache

from upstash_redis import Redis

from app.core.config import settings


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    return Redis(
        url=settings.UPSTASH_REDIS_REST_URL,
        token=settings.UPSTASH_REDIS_REST_TOKEN,
    )
