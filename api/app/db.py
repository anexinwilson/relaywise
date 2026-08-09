from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, func, select, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config.settings import settings


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"

    session_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    chat_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("conversations.session_id"), index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    sender: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=300)
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


def list_conversations(user_id: str) -> list[Conversation]:
    with SessionFactory() as session:
        return list(session.scalars(select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc()).limit(50)))


def list_messages(user_id: str, session_id: str) -> list[ConversationMessage]:
    with SessionFactory() as session:
        return list(session.scalars(select(ConversationMessage).where(Conversation.user_id == user_id, ConversationMessage.session_id == session_id).order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())))


def delete_conversation(user_id: str, session_id: str) -> int:
    with SessionFactory() as session:
        result = session.execute(delete(Conversation).where(Conversation.user_id == user_id, Conversation.session_id == session_id))
        session.commit()
        return result.rowcount or 0
