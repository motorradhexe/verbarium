"""Database engine and session handling.

Keeps SQLite and PostgreSQL interchangeable. The declarative base lives in
`app.db.base`.
"""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


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

    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True, future=True)

    if url.startswith("sqlite"):
        # SQLite ignores foreign keys unless asked, per connection. Without
        # this, ON DELETE RESTRICT and CASCADE are silently no-ops and the two
        # backends behave differently.
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
