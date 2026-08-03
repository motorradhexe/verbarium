"""Shared schema building blocks."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from app.db.base import ensure_utc


def _as_utc(value: object) -> object:
    return ensure_utc(value) if isinstance(value, datetime) else value


#: A timestamp that always serialises with an explicit UTC offset.
#:
#: Without this the same field comes back in two shapes on SQLite: an object
#: just created still holds the timezone-aware value Python wrote, while one
#: read back from the database is naive, because SQLite has no timezone type.
#: A client parsing the naive form would read it as local time.
UtcDatetime = Annotated[datetime, BeforeValidator(_as_utc)]


class VersionedUpdate(BaseModel):
    """A write that names the version it was based on. → D4

    Required rather than optional: a lock check a client may omit is no lock
    at all, and every caller that edits an entity has just read it, so it
    holds the version already.
    """

    version: int = Field(
        description="The version you loaded. The write is refused if the entity has moved on."
    )
