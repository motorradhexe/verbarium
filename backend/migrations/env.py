"""Alembic environment.

The database URL comes from the application settings rather than
`alembic.ini`, so migrations always target the same database the app does —
SQLite or PostgreSQL, whichever is configured.
"""

from logging.config import fileConfig

from alembic import context

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine

# Importing the models package registers every table on Base.metadata.
import app.models  # noqa: F401  isort:skip

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _configure(**kwargs: object) -> None:
    context.configure(
        target_metadata=target_metadata,
        # SQLite cannot ALTER most things; batch mode rewrites the table
        # instead. Harmless on PostgreSQL, essential on SQLite.
        render_as_batch=True,
        compare_type=True,
        compare_server_default=True,
        **kwargs,
    )


def run_migrations_offline() -> None:
    """Emit SQL without connecting to a database."""
    _configure(
        url=get_settings().sqlalchemy_url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the configured database."""
    with engine.connect() as connection:
        _configure(connection=connection)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
