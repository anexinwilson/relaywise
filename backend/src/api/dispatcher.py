from __future__ import annotations

import json
import uuid

import boto3

from config import settings
from memory import ChatMemory
from observability import logger, metrics

sqs = boto3.client("sqs", region_name=settings.AWS_REGION)


def _bounded_title(message: str) -> str:
    words = " ".join(message.strip().split()).split(" ")
    title = " ".join(words[:8]).strip(" .,!?:;")
    return title[:80] or "New conversation"


@logger.inject_lambda_context
def handler(event: dict, context: object) -> dict:
    """AppSync Lambda resolver: validate, account, and enqueue one task."""
    del context
    args = event.get("arguments", {})
    identity = event.get("identity", {})
    user_id = identity.get("resolverContext", {}).get("userId")
    message = args.get("message")
    session_id = args.get("sessionId") or str(uuid.uuid4())
    if not user_id or not isinstance(message, str) or not message.strip():
        raise ValueError("Authenticated user and non-empty message are required")

    chat_memory = ChatMemory()
    chat_name = chat_memory.get_chat_name(user_id, session_id)
    if chat_name is None:
        chat_name = _bounded_title(message)
        chat_memory.store_message(user_id, session_id, chat_name, "ASSISTANT", is_chat_name=True)

    task_id = str(uuid.uuid4())
    sqs.send_message(
        QueueUrl=settings.SQS_QUEUE_URL,
        MessageBody=json.dumps(
            {
                "taskId": task_id,
                "userId": user_id,
                "sessionId": session_id,
                "message": message,
                "chatName": chat_name,
            }
        ),
        MessageGroupId=session_id,
        MessageDeduplicationId=task_id,
    )
    metrics.add_metric(name="TaskAccepted", unit="Count", value=1)
    logger.info("Task accepted", task_id=task_id, session_id=session_id)
    return {
        "success": True,
        "taskId": task_id,
        "sessionId": session_id,
        "response": "Processing your request...",
        "chatName": chat_name,
    }
