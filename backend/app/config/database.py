from collections.abc import AsyncGenerator
from datetime import datetime
import uuid

from sqlalchemy import String, DateTime, func, Text, JSON, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config.settings import settings


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    clerk_user_id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    composio_user_id: Mapped[str | None] = mapped_column()
    composio_mcp_calls: Mapped[int] = mapped_column(default=0)
    llm_token_count: Mapped[int] = mapped_column(default=0)
    tier: Mapped[str] = mapped_column(default="free")
    daily_workflow_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    @property
    def display_name(self) -> str:
        return self.name or self.email.split('@')[0]


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"proj_{uuid.uuid4().hex[:16]}")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.clerk_user_id"))
    name: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class IntegrationConnection(Base):
    __tablename__ = "integration_connections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"conn_{uuid.uuid4().hex[:16]}")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    app_name: Mapped[str] = mapped_column()
    status: Mapped[str] = mapped_column(default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CompiledInstruction(Base):
    __tablename__ = "compiled_instructions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"instr_{uuid.uuid4().hex[:16]}")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column()
    spec: Mapped[dict] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(default=1)
    monitoring_mode: Mapped[str] = mapped_column(default="instant")
    check_interval: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"exec_{uuid.uuid4().hex[:16]}")
    instruction_id: Mapped[str] = mapped_column(ForeignKey("compiled_instructions.id"))
    status: Mapped[str] = mapped_column()
    cost: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"chat_{uuid.uuid4().hex[:16]}")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    role: Mapped[str] = mapped_column()
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session