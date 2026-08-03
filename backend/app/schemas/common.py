"""Shared schema building blocks."""

from datetime import datetime
from typing import Annotated

from pydantic import BeforeValidator

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
