"""Connected-app bookkeeping held in Redis.

Composio owns the connections themselves. Redis holds a per-user cache of which
toolkits are connected, plus a reverse index so an inbound webhook naming only a
connected-account id can find its owner.
"""

from __future__ import annotations

from app.clients import get_redis
from app.core.telemetry import logger

CONNECTED_APPS_KEY = "connected_apps:{user_id}"
ACCOUNT_OWNER_KEY = "account_owner:{account_id}"


def forget_connection(account_id: str, toolkit_slug: str) -> bool:
    """Drop a connection from the cache once Composio reports it expired.

    Returns True when an owner was found and the cache was updated.
    """
    redis = get_redis()
    owner_key = ACCOUNT_OWNER_KEY.format(account_id=account_id)
    user_id = redis.get(owner_key)
    if not user_id:
        logger.info("No cached owner for expired connection", account_id=account_id)
        return False

    if isinstance(user_id, bytes):
        user_id = user_id.decode("utf-8")

    redis.hdel(CONNECTED_APPS_KEY.format(user_id=user_id), toolkit_slug)
    redis.delete(owner_key)
    logger.info(
        "Cleared expired connection",
        toolkit_slug=toolkit_slug,
        user_id=user_id,
    )
    return True
