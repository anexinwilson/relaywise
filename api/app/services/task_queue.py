"""Task submission onto the FIFO queue consumed by the agent worker.

The API deliberately does no agent work of its own. It validates, titles the
conversation, and hands off — AppSync resolvers time out at 30s and an agent run
takes minutes.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from app.clients import get_sqs
from app.core.config import settings
from app.core.telemetry import logger

MAX_TITLE_WORDS = 6
MAX_TITLE_CHARS = 60

# Openers that carry no meaning in a sidebar label. "see if i have any new
# messages" is a fine sentence and a poor title; "any new messages" is the
# part that identifies the conversation. Stripped in order, repeatedly, so
# "hey can you please check..." reduces cleanly.
FILLER_PREFIXES = (
    "hey", "hi", "hello", "ok", "okay", "so", "well", "just",
    "please", "pls", "kindly",
    "can you", "could you", "would you", "will you",
    "i want to", "i need to", "i'd like to", "i would like to",
    "help me", "let's", "lets", "go and", "go ahead and",
    "see if", "check if", "find out if", "tell me if",
    # After "see if" is peeled, "i have any new messages" still leads with a
    # pronoun that says nothing about the topic.
    "i have", "do i have", "have i", "there are", "there is",
)


@dataclass(frozen=True)
class QueuedTask:
    task_id: str
    session_id: str
    chat_name: str


def build_title(message: str) -> str:
    """A short label for the sidebar, derived from the opening message.

    Deliberately not an LLM call: a title is worth a few microseconds, not a
    model round trip on every new conversation. Stripping conversational
    openers gets most of the way there — "see if i have any new messages"
    becomes "Any new messages" rather than being truncated mid-sentence.
    """
    collapsed = " ".join(message.strip().split())

    # Peel openers until none match; requests often stack two or three.
    lowered = collapsed.lower()
    changed = True
    while changed:
        changed = False
        for prefix in FILLER_PREFIXES:
            if lowered.startswith(prefix + " "):
                collapsed = collapsed[len(prefix) + 1 :]
                lowered = collapsed.lower()
                changed = True
                break
            # A message that is *only* filler leaves nothing behind, and falls
            # through to the default title rather than becoming "Please".
            if lowered.strip(" .,!?:;") == prefix:
                collapsed = ""
                lowered = ""
                changed = True
                break

    words = collapsed.split(" ")[:MAX_TITLE_WORDS]
    title = " ".join(words).strip(" .,!?:;-")

    if not title:
        return "New conversation"

    # Capitalise the first letter without flattening the rest: "slack" should
    # not become "Slack" mid-word, and "Gmail" must stay "Gmail".
    return (title[0].upper() + title[1:])[:MAX_TITLE_CHARS]


def enqueue_task(*, user_id: str, session_id: str, message: str, chat_name: str) -> QueuedTask:
    """Publish one agent task.

    `MessageGroupId` is the session so that turns within one conversation are
    processed in order, while separate conversations still run concurrently.
    `MessageDeduplicationId` is the task id because the queue has
    content-based deduplication disabled — two identical messages in the same
    chat are legitimate and must not be collapsed.
    """
    task_id = str(uuid.uuid4())
    get_sqs().send_message(
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
    logger.info("Task enqueued", task_id=task_id)
    return QueuedTask(task_id=task_id, session_id=session_id, chat_name=chat_name)
