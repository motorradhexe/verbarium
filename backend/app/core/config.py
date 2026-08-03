"""Application configuration.

All settings are read from environment variables (see `.env.example` in the
repository root). Nothing here is Verbarium-domain specific yet — this is the
scaffolding every later feature hangs off.
"""

import json
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VERBARIUM_",
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---------------------------------------------------
    app_name: str = "Verbarium"
    version: str = "0.1.0"
    environment: Literal["development", "production"] = "development"
    log_level: str = "info"

    # --- API -----------------------------------------------------------
    api_prefix: str = "/api"
    # `NoDecode` keeps pydantic-settings from JSON-parsing the raw value, so
    # the validator below can accept a plain comma-separated list.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Accept `a,b` as well as a JSON list `["a", "b"]`."""
        if isinstance(value, str):
            raw = value.strip()
            if raw.startswith("["):
                return json.loads(raw)
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
        return value

    # --- Database ------------------------------------------------------
    # `sqlite` is the default for single-user and development setups,
    # `postgres` is recommended for team deployments.
    db_backend: Literal["sqlite", "postgres"] = "sqlite"

    # Full SQLAlchemy URL. When set, it wins over the individual settings
    # below — useful for managed databases or unusual connection options.
    database_url: str | None = None

    sqlite_path: str = "./data/verbarium.db"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "verbarium"
    postgres_password: str = "verbarium"
    postgres_db: str = "verbarium"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_url(self) -> str:
        """The effective database URL used by the engine."""
        if self.database_url:
            return self.database_url
        if self.db_backend == "postgres":
            return (
                f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        return f"sqlite+pysqlite:///{self.sqlite_path}"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — import this, not `Settings()` directly."""
    return Settings()
