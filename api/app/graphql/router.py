"""Dispatch an AppSync field to its resolver.

A registry rather than an if/elif chain: adding a field means adding one entry
and one function, and a field present in the GraphQL schema but missing here
fails loudly instead of silently returning an "unknown field" object to the
browser.

Fields that return lists degrade to `[]` on error so the UI renders empty rather
than breaking; fields that return an object return an explicit error shape.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.telemetry import logger, metrics
from app.graphql.context import AppSyncRequest, UnauthorizedError
from app.graphql.resolvers import agent, conversation, user

Resolver = Callable[[AppSyncRequest], Any]

RESOLVERS: dict[str, Resolver] = {
    "askAgent": agent.ask_agent,
    "getUserConversations": conversation.list_conversations,
    "getConversationMessages": conversation.list_messages,
    "deleteConversation": conversation.delete_conversation,
    "getOrCreateUser": user.get_or_create_user,
}

# Fields whose GraphQL type is a list; their failure mode is an empty list.
LIST_FIELDS = frozenset({"getUserConversations", "getConversationMessages"})


def _empty_result(field_name: str, error: str) -> Any:
    if field_name in LIST_FIELDS:
        return []
    return {"success": False, "error": error}


def dispatch(event: dict[str, Any]) -> Any:
    request = AppSyncRequest.from_event(event)
    logger.append_keys(field_name=request.field_name, user_id=request.user_id)
    logger.info("Resolver invoked", argument_keys=sorted(request.arguments))

    resolver = RESOLVERS.get(request.field_name)
    if resolver is None:
        logger.error("No resolver registered for field")
        metrics.add_metric(name="ResolverError", unit="Count", value=1)
        return _empty_result(request.field_name, f"Unknown field: {request.field_name}")

    try:
        return resolver(request)
    except UnauthorizedError:
        logger.warning("Rejected unauthenticated request")
        return _empty_result(request.field_name, "Unauthorized")
    except Exception as exc:  # noqa: BLE001 - boundary: never 500 the whole API
        metrics.add_metric(name="ResolverError", unit="Count", value=1)
        logger.exception("Resolver failed", error_type=type(exc).__name__)
        return _empty_result(request.field_name, str(exc))
