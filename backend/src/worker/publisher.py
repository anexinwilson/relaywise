from __future__ import annotations

import json

import httpx

from config import settings


def publish_completion(
    *,
    task_id: str,
    user_id: str,
    status: str,
    result: dict | None = None,
    error: str | None = None,
    execution_time: int = 0,
) -> None:
    # AppSync delivers to subscribers only the fields selected *here*, intersected
    # with the subscriber's own selection set. Any field omitted below arrives as
    # null no matter what the payload carried — so `result` and `userId` must be
    # requested even though this caller ignores the response. Dropping `result`
    # leaves the browser with a completed task and no message to render.
    mutation = """
    mutation PublishTaskComplete($input: TaskCompleteInput!) {
      publishTaskComplete(input: $input) {
        taskId userId status result error executionTime timestamp
      }
    }
    """
    input_value = {
        "taskId": task_id,
        "userId": user_id,
        "status": status,
        # AppSync AWSJSON variables must be JSON-encoded strings at the
        # GraphQL boundary; sending a Python mapping is rejected as invalid.
        "result": json.dumps(result) if result is not None else None,
        "error": error,
        "executionTime": execution_time,
    }
    response = httpx.post(
        settings.APPSYNC_EVENTS_ENDPOINT,
        json={"query": mutation, "variables": {"input": input_value}},
        headers={"content-type": "application/json", "x-api-key": settings.APPSYNC_API_KEY},
        timeout=10,
    )
    response.raise_for_status()
    body = response.json()
    if body.get("errors"):
        raise RuntimeError(json.dumps(body["errors"]))
