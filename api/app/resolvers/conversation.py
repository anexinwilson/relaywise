from __future__ import annotations

from app.db import delete_conversation as delete_record
from app.db import list_conversations, list_messages


def get_user_conversations(obj, info, userId: str) -> list[dict]:
    del obj, info
    return [
        {
            "sessionId": item.session_id,
            "chatName": item.chat_name,
            "lastModifiedAt": item.updated_at.isoformat(),
        }
        for item in list_conversations(userId)
    ]


def get_conversation_messages(obj, info, userId: str, sessionId: str) -> list[dict]:
    del obj, info
    return [
        {
            "id": str(item.id),
            "sender": item.sender,
            "content": item.content,
            "timestamp": item.created_at.isoformat(),
            "type": item.sender.upper(),
        }
        for item in list_messages(userId, sessionId)
    ]


def delete_conversation(obj, info, userId: str, sessionId: str) -> dict:
    del obj, info
    deleted = delete_record(userId, sessionId)
    return {"success": True, "deletedCount": deleted}
