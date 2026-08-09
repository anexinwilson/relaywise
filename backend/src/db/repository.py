from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import Conversation, ConversationMessage


class ConversationRepository:
    """Owns user-visible conversation metadata, not LangGraph checkpoints."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, user_id: str, session_id: str) -> Conversation | None:
        return self.session.scalar(
            select(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.session_id == session_id,
            )
        )

    def upsert(self, user_id: str, session_id: str, chat_name: str | None = None) -> Conversation:
        conversation = self.get(user_id, session_id)
        if conversation is None:
            conversation = Conversation(
                user_id=user_id,
                session_id=session_id,
                chat_name=chat_name,
            )
            self.session.add(conversation)
        elif chat_name:
            conversation.chat_name = chat_name
        conversation.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        return conversation

    def list_for_user(self, user_id: str, limit: int = 50) -> list[Conversation]:
        return list(
            self.session.scalars(
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(Conversation.updated_at.desc())
                .limit(limit)
            )
        )

    def add_message(self, user_id: str, session_id: str, sender: str, content: str) -> ConversationMessage:
        message = ConversationMessage(
            user_id=user_id, session_id=session_id, sender=sender, content=content
        )
        self.session.add(message)
        self.session.commit()
        return message

    def list_messages(self, user_id: str, session_id: str) -> list[ConversationMessage]:
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
        result = self.session.execute(
            delete(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.session_id == session_id,
            )
        )
        self.session.commit()
        return result.rowcount or 0
