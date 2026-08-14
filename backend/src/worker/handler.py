from __future__ import annotations

import asyncio
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

    # Appended keys ride on every record emitted for this task, including those
    # from inside the agent (see utils.get_logger), so one CloudWatch filter on
    # task_id returns the whole story.
    logger.append_keys(task_id=task_id, session_id=session_id, user_id=user_id)
    metrics.add_metric(name="TaskStarted", unit="Count", value=1)
    logger.info("Task started", message_length=len(message))
    try:
        result = asyncio.run(
            get_agent_service().execute_task(
                user_message=message,
                user_id=user_id,
                conversation_id=session_id,
                chat_name=payload.get("chatName"),
            )
        )
        elapsed_ms = int((time.monotonic() - started) * 1000)
        succeeded = bool(result.get("success"))
        publish_completion(
            task_id=task_id,
            user_id=user_id,
            status="COMPLETED" if succeeded else "FAILED",
            result=result,
            error=None if succeeded else result.get("response"),
            execution_time=elapsed_ms,
        )
        if succeeded:
            metrics.add_metric(name="TaskCompleted", unit="Count", value=1)
            logger.info("Task completed", execution_time_ms=elapsed_ms)
        else:
            # The agent handled its own error and produced a user-facing
            # message. Report it as a failure so the metric means something,
            # but do not re-raise: retrying a refusal just burns tokens.
            metrics.add_metric(name="TaskFailed", unit="Count", value=1)
            logger.warning(
                "Task finished unsuccessfully",
                execution_time_ms=elapsed_ms,
                failure_kind="agent",
            )
    except Exception as exc:
        # Infrastructure failure: Neon, Mantle, Composio, or the publisher.
        # Re-raise so SQS retries and, after maxReceiveCount, routes to the DLQ.
        metrics.add_metric(name="TaskFailed", unit="Count", value=1)
        logger.exception(
            "Agent task raised",
            error_type=type(exc).__name__,
            failure_kind="infrastructure",
            execution_time_ms=int((time.monotonic() - started) * 1000),
        )
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
