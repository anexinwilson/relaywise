"""Resolver for `Query.askAgent`."""

from __future__ import annotations

import uuid

from app.core.telemetry import logger, metrics
from app.db import ConversationRepository, get_session_factory
from app.graphql.context import AppSyncRequest
from app.schemas import AgentResponse
from app.services.credits import check_credits, next_reset_label
from app.services.task_queue import build_title, enqueue_task

ACCEPTED_MESSAGE = "Processing your request..."
# This wording is duplicated in backend/src/agent/prompts.py, because the API
# and the worker ship as separate images with separate build contexts and share
# no code. The API refuses first — before a task is ever queued — so this is the
# copy a user actually reads. Change both, or the two will drift; they already
# did once.
OUT_OF_CREDITS_MESSAGE = (
    "You've used all your free credits for this month. "
    "They reset on {reset_date}."
)


def _resolve_chat_name(user_id: str, session_id: str, message: str) -> str:
    """Title the conversation from its first message only.

    Regenerating the title on every turn made the sidebar entry mutate as the
    conversation went on.
    """
    with get_session_factory()() as session:
        existing = ConversationRepository(session).get_chat_name(user_id, session_id)
    return existing or build_title(message)


def ask_agent(request: AppSyncRequest) -> dict:
    user_id = request.require_user_id()

    message = request.arguments.get("message")
    if not isinstance(message, str) or not message.strip():
        return AgentResponse(success=False, error="message is required").to_appsync()

    session_id = request.arguments.get("sessionId") or str(uuid.uuid4())
    logger.append_keys(session_id=session_id)

    # Refuse here rather than on the queue: a task that cannot run should never
    # cost a Lambda invocation or a cold start.
    has_credits, remaining = check_credits(user_id)
    if not has_credits:
        metrics.add_metric(name="TaskRefusedNoCredits", unit="Count", value=1)
        logger.warning("Task refused, no credits", remaining_credits=remaining)
        return AgentResponse(
            success=False,
            error=OUT_OF_CREDITS_MESSAGE.format(reset_date=next_reset_label()),
            sessionId=session_id,
        ).to_appsync()

    chat_name = _resolve_chat_name(user_id, session_id, message)
    task = enqueue_task(
        user_id=user_id,
        session_id=session_id,
        message=message,
        chat_name=chat_name,
    )

    metrics.add_metric(name="TaskAccepted", unit="Count", value=1)
    return AgentResponse(
        success=True,
        taskId=task.task_id,
        sessionId=task.session_id,
        response=ACCEPTED_MESSAGE,
        chatName=task.chat_name,
    ).to_appsync()
