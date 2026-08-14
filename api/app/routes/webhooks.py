"""Inbound webhooks from Composio.

This is the one surface that cannot go through AppSync: Composio's servers post
their own JSON shape and have no way to present a Clerk JWT.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.telemetry import logger
from app.services.integrations import forget_connection

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

CONNECTION_EXPIRED = "composio.connected_account.expired"


class Toolkit(BaseModel):
    slug: str | None = None


class ConnectionEventData(BaseModel):
    id: str | None = None
    toolkit: Toolkit = Field(default_factory=Toolkit)


class ComposioEvent(BaseModel):
    """Only the fields this service acts on; Composio sends more."""

    model_config = {"extra": "ignore"}

    type: str | None = None
    data: ConnectionEventData = Field(default_factory=ConnectionEventData)


@router.post("/composio")
async def composio_webhook(event: ComposioEvent) -> dict[str, bool]:
    """Acknowledge every event; act only on connection expiry.

    Always returns 200 — a non-2xx here makes Composio retry, and there is
    nothing to retry for an event type this service ignores.
    """
    if event.type != CONNECTION_EXPIRED:
        return {"success": True}

    account_id = event.data.id
    toolkit_slug = event.data.toolkit.slug
    if not account_id or not toolkit_slug:
        logger.warning("Expiry event missing account id or toolkit slug")
        return {"success": True}

    forget_connection(account_id, toolkit_slug)
    return {"success": True}
