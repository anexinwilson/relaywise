"""AppSync resolver for connected-app management.

The three actions here — connect, sync, disconnect — used to live on the
AgentCore Runtime alongside `ask_agent`, reached over HTTP at
COMPOSIO_CONTROL_URL. When AgentCore was removed, only `ask_agent` was rehomed
and these were dropped, which is why the integrations page stopped working.

They are user-initiated and authenticated, so AppSync is the right home: the
Clerk authorizer already establishes identity, and `resolverContext.userId` is
the only thing trusted here. The previous design sent `userId` in a request
body with no verification at all.

Deployed as its own Lambda from the *worker* image with an overridden
entrypoint, so the Composio SDK stays out of the API Lambda that serves
conversation queries on the hot path.
"""

from __future__ import annotations

import asyncio
from typing import Any

from agent.sync import (
    check_app_limit,
    disconnect_app,
    get_auth_url,
    sync_connections_to_redis,
)
from observability import logger, metrics

# Composio bills per connected account, so this caps what any one user can
# attach. The UI shows the same limit, but a client-side check is advisory —
# this is where it is actually enforced.
MAX_CONNECTED_APPS = 5


class UnauthorizedError(Exception):
    """No trusted identity on the request."""


def _user_id(event: dict[str, Any]) -> str:
    payload = event.get("payload", event)
    identity = (payload.get("identity") or {}).get("resolverContext") or {}
    if not identity:
        identity = (payload.get("request") or {}).get("headers") or {}
    user_id = identity.get("userId")
    if not user_id:
        raise UnauthorizedError("Authenticated user required")
    return user_id


def _arguments(event: dict[str, Any]) -> dict[str, Any]:
    return (event.get("payload", event)).get("arguments") or {}


def _field_name(event: dict[str, Any]) -> str:
    return ((event.get("payload", event)).get("info") or {}).get("fieldName", "")


def _connect(user_id: str, arguments: dict) -> dict:
    slug = (arguments.get("slug") or "").strip()
    if not slug:
        return {"success": False, "error": "slug is required"}

    if check_app_limit(user_id, MAX_CONNECTED_APPS):
        logger.warning("Connection refused, limit reached", limit=MAX_CONNECTED_APPS)
        return {
            "success": False,
            "error": (
                f"You can connect up to {MAX_CONNECTED_APPS} apps. "
                "Disconnect one to add another."
            ),
        }

    url = asyncio.run(get_auth_url(user_id, slug))
    if not url:
        return {"success": False, "error": f"Could not start authorization for {slug}"}

    metrics.add_metric(name="AppConnectStarted", unit="Count", value=1)
    logger.info("Authorization URL issued", toolkit_slug=slug)
    return {"success": True, "url": url}


def _sync(user_id: str, _arguments: dict) -> dict:
    connected = asyncio.run(sync_connections_to_redis(user_id))
    logger.info("Connections synced", connected_count=len(connected))
    return {"success": True, "connected": connected}


def _disconnect(user_id: str, arguments: dict) -> dict:
    slug = (arguments.get("slug") or "").strip()
    if not slug:
        return {"success": False, "error": "slug is required"}

    ok = asyncio.run(disconnect_app(user_id, slug))
    if not ok:
        return {"success": False, "error": f"Could not disconnect {slug}"}

    metrics.add_metric(name="AppDisconnected", unit="Count", value=1)
    logger.info("App disconnected", toolkit_slug=slug)
    # Re-sync so the caller gets the authoritative list back, rather than
    # trusting the client to guess what remains.
    connected = asyncio.run(sync_connections_to_redis(user_id))
    return {"success": True, "connected": connected}


RESOLVERS = {
    "connectApp": _connect,
    "syncConnections": _sync,
    "disconnectApp": _disconnect,
}


@logger.inject_lambda_context
@metrics.log_metrics
def handler(event: dict[str, Any], context: Any) -> dict:
    del context
    field_name = _field_name(event)
    logger.append_keys(field_name=field_name)

    resolver = RESOLVERS.get(field_name)
    if resolver is None:
        logger.error("No resolver registered for field")
        return {"success": False, "error": f"Unknown field: {field_name}"}

    try:
        user_id = _user_id(event)
        logger.append_keys(user_id=user_id)
        return resolver(user_id, _arguments(event))
    except UnauthorizedError:
        logger.warning("Rejected unauthenticated request")
        return {"success": False, "error": "Unauthorized"}
    except Exception as exc:  # noqa: BLE001 - boundary, never 500 to AppSync
        metrics.add_metric(name="IntegrationsError", unit="Count", value=1)
        logger.exception("Integrations resolver failed", error_type=type(exc).__name__)
        return {"success": False, "error": str(exc)}
