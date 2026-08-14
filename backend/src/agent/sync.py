"""
sync.py — Composio account management and Redis synchronization.
Handles: listing connections, syncing to Redis, disconnecting apps, connection limits.
"""
import asyncio
from utils import get_logger
from .client import get_composio_client, get_redis_client, get_executor

logger = get_logger(__name__)

_TTL_7_DAYS = 604800

async def sync_connections_to_redis(user_id: str) -> list[str]:
    """Make Redis match Composio exactly, and return the connected slugs.

    Authoritative, not additive. The previous version merged active connections
    into the hash and never removed entries that had gone inactive, so a
    revoked app kept showing as connected until the 7-day TTL expired.
    """
    sdk = get_composio_client()
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        get_executor(),
        lambda: sdk.connected_accounts.list(user_ids=[user_id], statuses=["ACTIVE"])
    )

    # SDK returns a response object — access .items for the connection list
    all_connections = getattr(response, "items", response) or []
    mapping = {c.toolkit.slug: c.id for c in all_connections}

    redis = get_redis_client()
    redis_key = f"connected_apps:{user_id}"

    stale = set(redis.hkeys(redis_key) or []) - set(mapping)
    if stale:
        redis.hdel(redis_key, *stale)
        logger.info("Dropped %s stale connections for %s: %s", len(stale), user_id, sorted(stale))

    if mapping:
        redis.hmset(redis_key, mapping)
        redis.expire(redis_key, _TTL_7_DAYS)

        # Reverse index for webhook lookups: account_owner:{accountId} -> user_id
        for account_id in mapping.values():
            redis.set(f"account_owner:{account_id}", user_id, ex=_TTL_7_DAYS)

    logger.info("Synced %s connections for user %s", len(mapping), user_id)
    return sorted(mapping)


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


def connected_slugs(user_id: str) -> list[str] | None:
    """Which toolkits this user has connected, straight from the Redis cache.

    Free compared with asking the model: no tokens, no round trip.

    Returns None — not [] — when Redis cannot be reached. The caller treats an
    empty list as "this user has connected nothing" and says so, which would be
    a lie during an outage. Unknown and empty are different answers.
    """
    try:
        return sorted(get_redis_client().hkeys(f"connected_apps:{user_id}") or [])
    except Exception as exc:
        logger.error(f"Failed to read connected apps: {exc}")
        return None


def check_app_limit(user_id: str, limit: int = 5) -> bool:
    """Returns True if the user has reached or exceeded the app connection limit."""
    try:
        redis = get_redis_client()
        count = redis.hlen(f"connected_apps:{user_id}")
        return count >= limit
    except Exception as e:
        logger.error(f"Failed to check app limit: {e}")
        return False  # Fail open — don't block the user on Redis errors


async def get_auth_url(user_id: str, app_slug: str) -> str | None:
    """Generate a Composio managed auth URL using the same pattern as the agent."""
    try:
        from config import settings
        sdk = get_composio_client()
        loop = asyncio.get_event_loop()

        session = await loop.run_in_executor(
            get_executor(),
            lambda: sdk.sessions.create(
                user_id=user_id,
                toolkits=[app_slug],
                manage_connections={
                    "enable": True,
                    "callback_url": settings.CALLBACK_URL,
                },
                sandbox={"enable": False},
            )
        )

        auth_request = await loop.run_in_executor(
            get_executor(),
            lambda: session.authorize(app_slug)
        )

        url = getattr(auth_request, "redirect_url", None) or getattr(auth_request, "redirectUrl", None)
        logger.info(f"Generated auth URL for {app_slug}: {url}")
        return url
    except Exception as e:
        logger.error(f"Failed to generate auth URL for {app_slug}: {e}")
        return None


# How long a conversation keeps pointing at the app it last used. Long enough
# for a session, short enough that a stale subject does not haunt a chat
# resumed days later.
_RECENT_APP_TTL = 86_400


# Habits decay: an app untouched for three months stops steering new chats.
_USAGE_TTL = 90 * 86_400


def _recent_app_key(user_id: str, session_id: str) -> str:
    return f"recent_app:{user_id}:{session_id}"


def _usage_key(user_id: str) -> str:
    return f"app_usage:{user_id}"


def get_recent_app(user_id: str, session_id: str) -> str | None:
    """The app this conversation last used, if any."""
    try:
        value = get_redis_client().get(_recent_app_key(user_id, session_id))
        return value.decode() if isinstance(value, bytes) else value
    except Exception as exc:
        logger.error(f"Failed to read recent app: {exc}")
        return None


def set_recent_app(user_id: str, session_id: str, slug: str) -> None:
    """Remember the subject of this conversation, and the user's habits.

    Two scopes, because they answer different questions:

    - per session: "what is *this* chat about" — dies with the conversation
    - per user:    "what does this person actually use" — survives it, so a
                   brand new chat is not back to square one

    The second is a sorted set rather than a single value: someone who uses
    Slack daily and tried Discord once should not have one experiment
    outrank months of habit.
    """
    try:
        redis = get_redis_client()
        redis.set(_recent_app_key(user_id, session_id), slug, ex=_RECENT_APP_TTL)
        redis.zincrby(_usage_key(user_id), 1, slug)
        redis.expire(_usage_key(user_id), _USAGE_TTL)
    except Exception as exc:
        logger.error(f"Failed to store recent app: {exc}")


def preferred_app(user_id: str, connected: list[str]) -> str | None:
    """The app this user reaches for most, restricted to what is connected.

    Used only when a new conversation gives no other signal. Returns None
    rather than guessing when there is no history.
    """
    if not connected:
        return None
    try:
        ranked = get_redis_client().zrange(
            _usage_key(user_id), 0, -1, rev=True, withscores=False
        ) or []
    except Exception as exc:
        logger.error(f"Failed to read app usage: {exc}")
        return None

    connected_set = set(connected)
    for slug in ranked:
        slug = slug.decode() if isinstance(slug, bytes) else slug
        if slug in connected_set:
            return slug
    return None
