from __future__ import annotations

import json
import time
from typing import Any

from aws_lambda_powertools.utilities.batch import (
    BatchProcessor,
    EventType,
    process_partial_response,
)
from aws_lambda_powertools.utilities.typing import LambdaContext

from agent.service import get_agent_service
from observability import logger, metrics
from .publisher import publish_completion

processor = BatchProcessor(event_type=EventType.SQS)


def _handle_record(record: dict[str, Any]) -> None:
    payload = json.loads(record["body"])
    task_id = payload["taskId"]
    user_id = payload["userId"]
    session_id = payload["sessionId"]
    message = payload["message"]
    started = time.monotonic()

    logger.append_keys(task_id=task_id, session_id=session_id)
    metrics.add_metric(name="TaskStarted", unit="Count", value=1)
    try:
        import asyncio

        result = asyncio.run(
            get_agent_service().execute_task(
                user_message=message,
                user_id=user_id,
                conversation_id=session_id,
                chat_name=payload.get("chatName"),
            )
        )
        elapsed_ms = int((time.monotonic() - started) * 1000)
        publish_completion(
            task_id=task_id,
            user_id=user_id,
            status="COMPLETED" if result.get("success") else "FAILED",
            result=result,
            error=None if result.get("success") else result.get("response"),
            execution_time=elapsed_ms,
        )
        metrics.add_metric(name="TaskCompleted", unit="Count", value=1)
    except Exception as exc:
        metrics.add_metric(name="TaskFailed", unit="Count", value=1)
        logger.exception("Agent task failed", error_type=type(exc).__name__)
        raise


@logger.inject_lambda_context
@metrics.log_metrics
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, list[dict[str, str]]]:
    return process_partial_response(
        event=event,
        record_handler=_handle_record,
        processor=processor,
        context=context,
    )
