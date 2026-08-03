import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models import Concept, Language, TermEntry, User
from app.models.enums import Role

#: Long enough for the default minimum password length.
ADMIN_PASSWORD = "correct-horse-battery-staple"
USER_PASSWORD = "another-long-enough-passphrase"


def _postgres_test_engine():
    """Engine for a dedicated `<database>_test` database, created if missing.

    These tests drop and recreate every table. Running them against the
    configured database would destroy a developer's working data the moment
    they point the suite at their own PostgreSQL, so the suite never touches
    it — it uses a sibling database and creates it on first use.
    """
    configured = make_url(get_settings().sqlalchemy_url)
    test_url = configured.set(database=f"{configured.database}_test")

    maintenance = create_engine(configured.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with maintenance.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": test_url.database},
        ).scalar()
        if not exists:
            # Identifier, so it cannot be bound as a parameter.
            connection.execute(text(f'CREATE DATABASE "{test_url.database}"'))
    maintenance.dispose()

    return create_engine(test_url)


@pytest.fixture
def db(tmp_path) -> Iterator[Session]:
    """A throwaway database with the full schema, on the configured backend.

    Follows `VERBARIUM_DB_BACKEND` so that CI exercises these guarantees on
    PostgreSQL as well — foreign key behaviour, check constraints, and type
    handling are exactly where the two backends differ.

    Built with `create_all` rather than by running migrations; a separate test
    asserts that the migrations produce the same schema.
    """
    settings = get_settings()

    if settings.db_backend == "postgres":
        engine = _postgres_test_engine()
    else:
        engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'test.db'}")

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def user(db: Session) -> User:
    account = User(
        email="editor@example.org",
        display_name="Editor",
        password_hash="not-a-real-hash",
        role=Role.EDITOR,
    )
    db.add(account)
    db.commit()
    return account


@pytest.fixture
def languages(db: Session) -> list[Language]:
    configured = [
        Language(code="de", name="German", position=0),
        Language(code="en", name="English", position=1),
    ]
    db.add_all(configured)
    db.commit()
    return configured


@pytest.fixture
def concept(db: Session, user: User) -> Concept:
    entry = Concept(created_by_id=user.id)
    db.add(entry)
    db.commit()
    return entry


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """A test client whose requests use the test database."""
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def admin(db: Session) -> User:
    account = User(
        email="admin@example.org",
        display_name="Admin",
        password_hash=hash_password(ADMIN_PASSWORD),
        role=Role.ADMIN,
    )
    db.add(account)
    db.commit()
    return account


def sign_in(client: TestClient, email: str, password: str) -> None:
    """Log in, leaving the session cookie on the client."""
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def make_term(concept: Concept, user: User, language: str, term: str, **kwargs) -> TermEntry:
    return TermEntry(
        id=uuid.uuid4(),
        concept_id=concept.id,
        language_code=language,
        term=term,
        created_by_id=user.id,
        **kwargs,
    )
