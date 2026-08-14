"""FastAPI application factory.

The HTTP surface is deliberately small: a health check and the Composio webhook.
Everything the browser calls goes through AppSync instead, so it inherits the
Clerk authorizer rather than needing its own auth layer here.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import health, webhooks

DEFAULT_ALLOWED_ORIGINS = ["http://localhost:3000"]


def _allowed_origins() -> list[str]:
    """Comma-separated override so the deployed frontend can be added without a
    code change."""
    configured = os.getenv("CORS_ALLOWED_ORIGINS", "")
    origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
    return origins or DEFAULT_ALLOWED_ORIGINS


def create_app() -> FastAPI:
    app = FastAPI(
        title="Relaywise API",
        description="Webhook and health surface for the Relaywise agent platform.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(webhooks.router)
    return app


app = create_app()
