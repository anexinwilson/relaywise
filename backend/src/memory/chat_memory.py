"""Conversation metadata facade backed by SQLAlchemy."""

from __future__ import annotations

from db.repository import ConversationRepository
from db.session import get_session_factory


class ChatMemory:
    """Stores titles and listing metadata; LangGraph stores message state."""

    def __init__(self) -> None:
        self.session_factory = get_session_factory()

    def get_chat_name(self, actor_id: str, session_id: str) -> str | None:
        with self.session_factory() as session:
            conversation = ConversationRepository(session).get(actor_id, session_id)
            return conversation.chat_name if conversation else None

    def save_chat_name(self, actor_id: str, session_id: str, chat_name: str | None) -> None:
        with self.session_factory() as session:
            ConversationRepository(session).upsert(actor_id, session_id, chat_name=chat_name)

    def append_message(self, actor_id: str, session_id: str, role: str, message: str) -> None:
        if not message:
            return
        with self.session_factory() as session:
            repository = ConversationRepository(session)
            repository.upsert(actor_id, session_id)
            repository.add_message(actor_id, session_id, role, message)

    def get_chat_names(self, actor_id: str, max_results: int = 50) -> list[dict]:
        with self.session_factory() as session:
            conversations = ConversationRepository(session).list_for_user(
                actor_id, max_results
            )
            return [
                {
                    "session_id": item.session_id,
                    "title": item.chat_name or "Untitled",
                    "created_at": item.created_at.isoformat(),
                    "updated_at": item.updated_at.isoformat(),
                }
                for item in conversations
            ]
