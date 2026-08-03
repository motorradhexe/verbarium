"""Migration tests.

The model tests build their schema with `create_all`. That says nothing about
whether the migrations produce the same thing — and the migrations are what
actually runs against a deployed database.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.db.base import Base

BACKEND_DIR = Path(__file__).resolve().parent.parent

EXPECTED_TABLES = {
    "workspace_settings",
    "languages",
    "users",
    "domains",
    "concepts",
    "concept_domains",
    "term_entries",
    "change_history",
    "review_comments",
}


def run_alembic(*args: str, database: Path) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env={
            **os.environ,
            "VERBARIUM_DB_BACKEND": "sqlite",
            "VERBARIUM_SQLITE_PATH": str(database),
        },
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"alembic {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}")
    return result


@pytest.fixture
def migrated_database(tmp_path) -> Path:
    database = tmp_path / "migrated.db"
    run_alembic("upgrade", "head", database=database)
    return database


def test_upgrade_creates_every_table(migrated_database: Path):
    engine = create_engine(f"sqlite+pysqlite:///{migrated_database}")

    tables = set(inspect(engine).get_table_names())

    assert EXPECTED_TABLES <= tables


def test_the_migrated_schema_matches_the_models(migrated_database: Path):
    """Catches a model change that nobody generated a migration for."""
    engine = create_engine(f"sqlite+pysqlite:///{migrated_database}")

    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        differences = compare_metadata(context, Base.metadata)

    assert differences == [], f"Models and migrations have drifted apart: {differences}"


def test_downgrade_removes_everything(migrated_database: Path):
    run_alembic("downgrade", "base", database=migrated_database)
    engine = create_engine(f"sqlite+pysqlite:///{migrated_database}")

    remaining = set(inspect(engine).get_table_names()) - {"alembic_version"}

    assert remaining == set()
