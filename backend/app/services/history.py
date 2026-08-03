"""Change history recording.

Written automatically on every write. Answers *what* changed; the reasoning
lives in review comments. → D6
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import HistoryEntityType
from app.models.history import ChangeHistoryEntry
from app.models.user import User

#: Fields whose changes are not worth a history row. `search_text` is derived,
#: `version` and `updated_at` are bookkeeping.
IGNORED_FIELDS = frozenset({"search_text", "version", "updated_at", "id"})


class StaleVersion(Exception):
    """The write was based on a version that has since moved on. → D4"""

    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(f"expected version {expected}, current is {actual}")
        self.expected = expected
        self.actual = actual


def check_version(entity: Any, expected: int) -> None:
    """Refuse a write built on a stale read.

    SQLAlchemy's `version_id_col` guards a session that held the object across
    the change; it cannot help here, because each request loads the row fresh
    and therefore always sees the current version. The client's version is the
    only evidence of what it actually edited.
    """
    if entity.version != expected:
        raise StaleVersion(expected=expected, actual=entity.version)


def _render(value: Any) -> str | None:
    """One column value as text, so one table can record every type."""
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def snapshot(entity: Any, fields: list[str]) -> dict[str, Any]:
    """The values to compare against after a change."""
    return {field: getattr(entity, field) for field in fields}


def record_changes(
    db: Session,
    *,
    entity_type: HistoryEntityType,
    entity_id: uuid.UUID,
    before: dict[str, Any],
    after: dict[str, Any],
    changed_by: User,
) -> list[ChangeHistoryEntry]:
    """Write one row per field that actually changed.

    Not flushed here — the caller commits, so the history and the change it
    describes land in the same transaction.
    """
    written = []

    for field, old_value in before.items():
        if field in IGNORED_FIELDS:
            continue

        new_value = after.get(field)
        if old_value == new_value:
            continue

        entry = ChangeHistoryEntry(
            entity_type=entity_type,
            entity_id=entity_id,
            field=field,
            old_value=_render(old_value),
            new_value=_render(new_value),
            changed_by_id=changed_by.id,
        )
        db.add(entry)
        written.append(entry)

    return written


def record_creation(
    db: Session,
    *,
    entity_type: HistoryEntityType,
    entity_id: uuid.UUID,
    changed_by: User,
) -> ChangeHistoryEntry:
    """A single row marking that the entity came into existence."""
    entry = ChangeHistoryEntry(
        entity_type=entity_type,
        entity_id=entity_id,
        field="created",
        old_value=None,
        new_value="created",
        changed_by_id=changed_by.id,
    )
    db.add(entry)
    return entry


def history_for(
    db: Session, entity_type: HistoryEntityType, entity_id: uuid.UUID
) -> list[ChangeHistoryEntry]:
    """Newest first. Read-only to every role."""
    return list(
        db.scalars(
            select(ChangeHistoryEntry)
            .where(
                ChangeHistoryEntry.entity_type == entity_type,
                ChangeHistoryEntry.entity_id == entity_id,
            )
            .order_by(ChangeHistoryEntry.changed_at.desc())
        )
    )
