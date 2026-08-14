"""Lambda entrypoint.

One function serves two callers, so the first job is telling them apart:

- AppSync invokes it directly with a resolver payload -> `app.graphql.dispatch`
- API Gateway proxies HTTP requests -> the FastAPI app via Mangum

Everything below this file is plain Python that can be imported and tested
without a Lambda context.
"""

from __future__ import annotations

from typing import Any

from mangum import Mangum

from app.application import app
from app.core.telemetry import logger, metrics
from app.graphql import dispatch

_http_handler = Mangum(app)


def _is_appsync_event(event: dict[str, Any]) -> bool:
    payload = event.get("payload", event)
    return "fieldName" in (payload.get("info") or {})


@logger.inject_lambda_context
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: Any) -> Any:
    if _is_appsync_event(event):
        return dispatch(event)
    return _http_handler(event, context)


# Container image CMD target.
handler = lambda_handler
