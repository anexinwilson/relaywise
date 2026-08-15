"""Keep the free-tier data stores from going idle.

Neon and Upstash both reclaim resources on inactivity, and their free tiers are
the most aggressive about it. A project nobody touches for weeks can come back
suspended, or in the worst case gone, which is a problem for a portfolio piece:
the person most likely to open it is a stranger doing so months after it was
last worked on, and a demo that greets them with a connection error is worse
than no demo.

So a scheduled event runs the cheapest possible query against each store. The
point is not the result, it is the connection: a single read is enough to count
as activity.

This lives in the existing API Lambda rather than a service of its own. The
work is two queries, and a fifth function would mean another container image to
build, push, store and keep patched for no benefit. The API image already has
both clients.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.clients import get_redis
from app.core.telemetry import logger, metrics
from app.db import get_session_factory


def touch_stores() -> dict[str, Any]:
    """Read from Postgres and Redis so both register recent activity.

    Each store is tried independently and failures are recorded rather than
    raised. One being unreachable is worth knowing about, and is not a reason
    to skip the other.
    """
    results: dict[str, Any] = {}

    try:
        with get_session_factory()() as session:
            session.execute(text("SELECT 1"))
        results["postgres"] = "ok"
    except Exception as exc:
        results["postgres"] = f"{type(exc).__name__}: {exc}"
        logger.error("Keepalive could not reach Postgres", error=str(exc))

    try:
        # A read against a key that does not exist. Cheaper than a write and it
        # leaves nothing behind.
        get_redis().get("keepalive")
        results["redis"] = "ok"
    except Exception as exc:
        results["redis"] = f"{type(exc).__name__}: {exc}"
        logger.error("Keepalive could not reach Redis", error=str(exc))

    healthy = all(value == "ok" for value in results.values())
    metrics.add_metric(
        name="KeepaliveHealthy" if healthy else "KeepaliveFailed",
        unit="Count",
        value=1,
    )
    logger.info("Keepalive ran", **results)

    return {"healthy": healthy, **results}
