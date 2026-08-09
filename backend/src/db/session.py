from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import settings


def _database_url() -> str:
    # SQLAlchemy's psycopg dialect accepts the Neon URL without rewriting it.
    return settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        _database_url(),
        pool_pre_ping=True,
        pool_recycle=300,
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
