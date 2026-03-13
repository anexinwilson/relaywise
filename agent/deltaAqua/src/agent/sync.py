"""
sync.py — Composio account management and Redis synchronization.
Handles: listing connections, syncing to Redis, disconnecting apps, rate limit checks.
"""
import asyncio
import logging
from utils import get_logger
from .client import get_composio_client, get_redis_client, get_executor

logger = get_logger(__name__)

_TTL_7_DAYS = 604800

async def sync_connections_to_redis(user_id: str) -> None:
    """Fetch all active Composio connections for a user and write to Redis hash."""
    try:
        sdk = get_composio_client()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            get_executor(),
            lambda: sdk.connected_accounts.list(user_ids=[user_id], statuses=["ACTIVE"])
        )

        # SDK returns a response object — access .items for the connection list
        all_connections = getattr(response, "items", response) or []

        if not all_connections:
            return

        redis = get_redis_client()
        redis_key = f"connected_apps:{user_id}"

        # Hash: slug -> connectedAccountId (hmset for upstash-redis compatibility)
        mapping = {c.toolkit.slug: c.id for c in all_connections}
        if not mapping:
            return

        redis.hmset(redis_key, mapping)
        redis.expire(redis_key, _TTL_7_DAYS)

        # Reverse index for webhook lookups: account_owner:{accountId} -> user_id
        for account_id in mapping.values():
            redis.set(f"account_owner:{account_id}", user_id, ex=_TTL_7_DAYS)

        logger.info(f"Synced {len(mapping)} connections to Redis for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to sync connections to Redis: {e}")


async def disconnect_app(user_id: str, app_slug: str, connected_account_id: str = None) -> bool:
    """Revoke a Composio connection and remove it from Redis."""
    try:
        redis = get_redis_client()
        redis_key = f"connected_apps:{user_id}"

        # 1. Look up account ID from Redis if not provided
        if not connected_account_id:
            connected_account_id = redis.hget(redis_key, app_slug)

        # 2. Revoke in Composio
        if connected_account_id:
            sdk = get_composio_client()
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                get_executor(),
                lambda: sdk.connected_accounts.delete(connected_account_id)
            )
            logger.info(f"Revoked {app_slug} ({connected_account_id}) in Composio")
        else:
            logger.warning(f"No connected account ID found for {app_slug}, skipping Composio revoke")

        # 3. Remove from Redis hash
        redis.hdel(redis_key, app_slug)

        # 4. Remove reverse index
        if connected_account_id:
            redis.delete(f"account_owner:{connected_account_id}")

        return True
    except Exception as e:
        logger.error(f"Failed to disconnect {app_slug}: {e}")
        return False


def check_app_limit(user_id: str, limit: int = 5) -> bool:
    """Returns True if the user has reached or exceeded the app connection limit."""
    try:
        redis = get_redis_client()
        count = redis.hlen(f"connected_apps:{user_id}")
        return count >= limit
    except Exception as e:
        logger.error(f"Failed to check app limit: {e}")
        return False  # Fail open — don't block the user on Redis errors


def handle_expired_webhook(event_type: str, data: dict) -> bool:
    """Handle Composio webhook for expired connections."""
    try:
        if event_type != "composio.connected_account.expired":
            return True

        account_id = data.get("id")
        slug = data.get("toolkit", {}).get("slug")

        if not account_id or not slug:
            return True

        redis = get_redis_client()
        owner_key = f"account_owner:{account_id}"
        user_id = redis.get(owner_key)

        if user_id:
            if isinstance(user_id, bytes):
                user_id = user_id.decode("utf-8")
            redis.hdel(f"connected_apps:{user_id}", slug)
            redis.delete(owner_key)
            logger.info(f"Cleaned up expired connection {slug} for user {user_id}")

        return True
    except Exception as e:
        logger.error(f"Webhook handler error: {e}")
        return False
