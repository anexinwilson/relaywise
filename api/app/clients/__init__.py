"""Third-party clients, constructed lazily and cached per Lambda container."""

from .redis import get_redis
from .sqs import get_sqs

__all__ = ["get_redis", "get_sqs"]
