"""Term entry operations."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.text import build_search_text
from app.models.concept import Concept
from app.models.enums import HistoryEntityType, TermStatus
from app.models.history import ReviewComment
from app.models.term import TermEntry
from app.models.user import User
from app.models.workspace import Language
from app.schemas.term import TermEntryCreate, TermEntryUpdate
from app.services import history, workflow

#: Fields the change history tracks on a term entry.
TRACKED_FIELDS = [
    "term",
    "definition",
    "synonyms",
    "nogo_alternatives",
    "context_example",
    "source",
    "notes",
    "status",
    "assignee_id",
]


class UnknownLanguage(Exception):
    """The language is not configured for this workspace. → D14"""


class LanguageAlreadyPresent(Exception):
    """The concept already holds an entry in this language."""


class UnknownAssignee(Exception):
    pass


def _refresh_search_text(entry: TermEntry) -> None:
    entry.search_text = build_search_text(
        entry.term, entry.definition, entry.synonyms, entry.nogo_alternatives
    )


def get_term(db: Session, term_id: uuid.UUID) -> TermEntry | None:
    return db.get(TermEntry, term_id)


def create_term(
    db: Session, concept: Concept, request: TermEntryCreate, user: User, *, commit: bool = True
) -> TermEntry:
    """Add one language's entry to a concept.

    Starts as Draft regardless of who creates it — reaching any further status
    goes through the workflow, so nothing skips review by being created that
    way.
    """
    language = db.get(Language, request.language_code.lower())
    if language is None:
        raise UnknownLanguage(request.language_code)

    already_there = db.scalar(
        select(TermEntry).where(
            TermEntry.concept_id == concept.id,
            TermEntry.language_code == language.code,
        )
    )
    if already_there is not None:
        raise LanguageAlreadyPresent(language.code)

    entry = TermEntry(
        concept_id=concept.id,
        language_code=language.code,
        term=request.term,
        definition=request.definition,
        synonyms=list(request.synonyms),
        nogo_alternatives=list(request.nogo_alternatives),
        context_example=request.context_example,
        source=request.source,
        notes=request.notes,
        origin=request.origin,
        status=TermStatus.DRAFT,
        created_by_id=user.id,
    )
    _refresh_search_text(entry)
    db.add(entry)
    db.flush()

    history.record_creation(
        db, entity_type=HistoryEntityType.TERM_ENTRY, entity_id=entry.id, changed_by=user
    )

    if commit:
        db.commit()

    return entry


def update_term(db: Session, entry: TermEntry, request: TermEntryUpdate, user: User) -> TermEntry:
    """Apply the fields that were sent, recording each change.

    A substantive edit to an approved entry sends it back to Draft: an
    "Approved" badge has to mean somebody approved this wording, not an
    earlier one. → D19
    """
    history.check_version(entry, request.version)

    before = history.snapshot(entry, TRACKED_FIELDS)

    changes = request.model_dump(exclude_unset=True, exclude={"version"})
    for field, value in changes.items():
        setattr(entry, field, value)

    if changes:
        _refresh_search_text(entry)

    if workflow.needs_reapproval(entry, set(changes)):
        entry.status = TermStatus.DRAFT

    after = history.snapshot(entry, TRACKED_FIELDS)
    history.record_changes(
        db,
        entity_type=HistoryEntityType.TERM_ENTRY,
        entity_id=entry.id,
        before=before,
        after=after,
        changed_by=user,
    )
    db.commit()

    return entry


def delete_term(db: Session, entry: TermEntry) -> None:
    db.delete(entry)
    db.commit()


def transition(
    db: Session, entry: TermEntry, action: workflow.Action, comment: str | None, user: User
) -> TermEntry:
    """Move an entry through the workflow, recording why. → D6

    Raises the workflow's own exceptions, which the route turns into status
    codes — the distinction between "wrong status", "wrong role", and
    "comment missing" is worth keeping.
    """
    rules = workflow.check(entry, action, user, comment)

    before = history.snapshot(entry, TRACKED_FIELDS)
    entry.status = rules.to_status

    if comment and comment.strip():
        db.add(
            ReviewComment(
                term_entry_id=entry.id,
                author_id=user.id,
                body=comment.strip(),
                transition=rules.records_as,
            )
        )

    history.record_changes(
        db,
        entity_type=HistoryEntityType.TERM_ENTRY,
        entity_id=entry.id,
        before=before,
        after=history.snapshot(entry, TRACKED_FIELDS),
        changed_by=user,
    )
    db.commit()

    return entry


def assign(db: Session, entry: TermEntry, assignee_id: uuid.UUID | None, user: User) -> TermEntry:
    """Claim an entry, hand it over, or release it. → D2"""
    if assignee_id is not None:
        assignee = db.get(User, assignee_id)
        if assignee is None or not assignee.is_active:
            raise UnknownAssignee(str(assignee_id))

    before = history.snapshot(entry, TRACKED_FIELDS)
    entry.assignee_id = assignee_id

    history.record_changes(
        db,
        entity_type=HistoryEntityType.TERM_ENTRY,
        entity_id=entry.id,
        before=before,
        after=history.snapshot(entry, TRACKED_FIELDS),
        changed_by=user,
    )
    db.commit()

    return entry


def comments_for(db: Session, entry: TermEntry) -> list[ReviewComment]:
    return list(
        db.scalars(
            select(ReviewComment)
            .where(ReviewComment.term_entry_id == entry.id)
            .order_by(ReviewComment.created_at.desc())
        )
    )
