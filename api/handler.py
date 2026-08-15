"""Lambda entrypoint.

One function serves two callers, so the first job is telling them apart:

- AppSync invokes it directly with a resolver payload -> `app.graphql.dispatch`
- API Gateway proxies HTTP requests -> the FastAPI app via Mangum
- EventBridge sends a scheduled keepalive -> `app.services.keepalive`

Everything below this file is plain Python that can be imported and tested
without a Lambda context.
"""

from __future__ import annotations

from typing import Any

from mangum import Mangum

from app.application import app
from app.core.telemetry import logger, metrics
from app.graphql import dispatch
from app.services.keepalive import touch_stores

_http_handler = Mangum(app)


def _is_appsync_event(event: dict[str, Any]) -> bool:
    payload = event.get("payload", event)
    return "fieldName" in (payload.get("info") or {})


def _is_keepalive_event(event: dict[str, Any]) -> bool:
    """EventBridge scheduled events carry a fixed detail-type we set ourselves.

    Checked before the AppSync test because a scheduled event has neither an
    `info` block nor an HTTP envelope, and would otherwise fall through to
    Mangum and be parsed as a malformed request.
    """
    return event.get("detail-type") == "relaywise.keepalive"


@logger.inject_lambda_context
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: Any) -> Any:
    if _is_keepalive_event(event):
        return touch_stores()
    if _is_appsync_event(event):
        return dispatch(event)
    return _http_handler(event, context)


# Container image CMD target.
handler = lambda_handler
