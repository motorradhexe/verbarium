"""Database engine and session handling.

No models exist yet — this module only establishes the connection layer so
that SQLite and PostgreSQL are interchangeable from day one.
"""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all future ORM models."""


def _create_engine() -> Engine:
    settings = get_settings()
    url = settings.sqlalchemy_url

    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        # Make sure the directory for the database file exists.
        Path(settings.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        # FastAPI serves requests from a threadpool, so the connection may be
        # handed between threads.
        connect_args["check_same_thread"] = False

    return create_engine(url, connect_args=connect_args, pool_pre_ping=True, future=True)


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
