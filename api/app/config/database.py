from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy import String, DateTime, func
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
    api_call_count: Mapped[int] = mapped_column(default=0)
    tier: Mapped[str] = mapped_column(default="free")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


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