"""Data access for conversations.

All queries are scoped by `user_id` so a caller cannot read or delete another
Clerk user's data by guessing a session id.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import Conversation, ConversationMessage

MAX_CONVERSATIONS = 50


class ConversationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_chat_name(self, user_id: str, session_id: str) -> str | None:
        """Existing title, or None when this is the conversation's first message."""
        return self.session.scalar(
            select(Conversation.chat_name).where(
                Conversation.user_id == user_id,
                Conversation.session_id == session_id,
            )
        )

    def list_for_user(self, user_id: str, limit: int = MAX_CONVERSATIONS) -> list[Conversation]:
        return list(
            self.session.scalars(
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(Conversation.updated_at.desc())
                .limit(limit)
            )
        )

    def list_messages(self, user_id: str, session_id: str) -> list[ConversationMessage]:
        # Both predicates target ConversationMessage. Filtering on Conversation
        # here would add an implicit cross join and return every message once
        # per conversation the user owns.
        return list(
            self.session.scalars(
                select(ConversationMessage)
                .where(
                    ConversationMessage.user_id == user_id,
                    ConversationMessage.session_id == session_id,
                )
                .order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())
            )
        )

    def delete(self, user_id: str, session_id: str) -> int:
        """Delete a conversation. Messages cascade via the foreign key."""
        result = self.session.execute(
            delete(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.session_id == session_id,
            )
        )
        self.session.commit()
        return result.rowcount or 0
