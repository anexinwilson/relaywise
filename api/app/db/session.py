"""Database engine and session factory.

The engine is created lazily and cached so that a Lambda cold start pays for it
once and warm invocations reuse the pool. `pool_pre_ping` matters here because
Neon closes idle connections between invocations.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _database_url() -> str:
    # SQLAlchemy needs the driver spelled out; Neon hands out a bare
    # postgresql:// URL.
    return settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    engine = create_engine(_database_url(), pool_pre_ping=True, pool_recycle=300)
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a session that always closes."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
