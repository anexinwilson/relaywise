"""Resolvers for conversation history.

Reads and deletes only. The worker owns all writes to these tables.
"""

from __future__ import annotations

from app.core.telemetry import logger
from app.db import ConversationRepository, get_session_factory
from app.graphql.context import AppSyncRequest
from app.schemas import ConversationSummary, DeleteResponse, MessageView


def list_conversations(request: AppSyncRequest) -> list[dict]:
    user_id = request.require_user_id()
    with get_session_factory()() as session:
        conversations = ConversationRepository(session).list_for_user(user_id)

    logger.info("Conversations listed", conversation_count=len(conversations))
    return [
        ConversationSummary(
            sessionId=item.session_id,
            chatName=item.chat_name,
            lastModifiedAt=item.updated_at.isoformat(),
        ).to_appsync()
        for item in conversations
    ]


def list_messages(request: AppSyncRequest) -> list[dict]:
    user_id = request.require_user_id()
    session_id = request.arguments.get("sessionId")
    if not session_id:
        logger.warning("sessionId missing")
        return []

    logger.append_keys(session_id=session_id)
    with get_session_factory()() as session:
        messages = ConversationRepository(session).list_messages(user_id, session_id)

    logger.info("Messages listed", message_count=len(messages))
    return [
        MessageView(
            id=str(item.id),
            sender=item.sender,
            content=item.content,
            timestamp=item.created_at.isoformat(),
            type=item.sender.upper(),
        ).to_appsync()
        for item in messages
    ]


def delete_conversation(request: AppSyncRequest) -> dict:
    user_id = request.require_user_id()
    session_id = request.arguments.get("sessionId")
    if not session_id:
        return DeleteResponse(success=False, error="sessionId is required").to_appsync()

    logger.append_keys(session_id=session_id)
    with get_session_factory()() as session:
        deleted = ConversationRepository(session).delete(user_id, session_id)

    logger.info("Conversation deleted", deleted_count=deleted)
    return DeleteResponse(success=True, deletedCount=deleted).to_appsync()
