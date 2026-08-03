"""Concept operations, including the term list. → D12"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.text import normalise
from app.models.concept import Concept, Domain
from app.models.enums import ConceptLifecycle, HistoryEntityType, TermStatus
from app.models.term import TermEntry
from app.models.user import User
from app.schemas.concept import ConceptCreate, ConceptUpdate
from app.services import history, terms

TRACKED_FIELDS = ["lifecycle", "superseded_by_id"]


class UnknownDomain(Exception):
    pass


class UnknownSuccessor(Exception):
    pass


class SuccessorMustDiffer(Exception):
    """A concept cannot supersede itself. → D7"""


@dataclass
class ConceptFilters:
    """What the term list can be narrowed by. → D12"""

    #: Free text over term, definition, synonyms, and NoGo alternatives. → D16
    query: str | None = None
    #: Only concepts that have an entry in this language.
    language: str | None = None
    #: Only concepts that *lack* an entry in this language — the gap filter.
    #: Ordinary filters work on what exists; the common management question is
    #: about what does not.
    missing_language: str | None = None
    #: Any entry in one of these statuses.
    statuses: list[TermStatus] = field(default_factory=list)
    domain_ids: list[uuid.UUID] = field(default_factory=list)
    assignee_id: uuid.UUID | None = None
    lifecycle: ConceptLifecycle | None = None
    limit: int = 50
    offset: int = 0


def _with_relations(statement):
    return statement.options(
        selectinload(Concept.domains), selectinload(Concept.term_entries)
    )


def get_concept(db: Session, concept_id: uuid.UUID) -> Concept | None:
    return db.scalar(_with_relations(select(Concept).where(Concept.id == concept_id)))


def _resolve_domains(db: Session, domain_ids: list[uuid.UUID]) -> list[Domain]:
    if not domain_ids:
        return []

    found = list(db.scalars(select(Domain).where(Domain.id.in_(domain_ids))))
    if len(found) != len(set(domain_ids)):
        missing = set(domain_ids) - {domain.id for domain in found}
        raise UnknownDomain(", ".join(str(identifier) for identifier in sorted(missing, key=str)))

    return found


def create_concept(db: Session, request: ConceptCreate, user: User) -> Concept:
    """Create a concept together with any entries supplied.

    One transaction: a concept that exists while its first entry failed
    validation is not a state worth leaving behind.
    """
    try:
        concept = Concept(created_by_id=user.id)
        concept.domains = _resolve_domains(db, request.domain_ids)
        db.add(concept)
        db.flush()

        history.record_creation(
            db, entity_type=HistoryEntityType.CONCEPT, entity_id=concept.id, changed_by=user
        )

        for entry in request.terms:
            terms.create_term(db, concept, entry, user, commit=False)

        db.commit()
    except Exception:
        # Explicit, rather than relying on the request's session being
        # discarded: a rejected entry must not leave a bare concept behind,
        # and the guarantee should not depend on who owns the session.
        db.rollback()
        raise

    return concept


def update_concept(db: Session, concept: Concept, request: ConceptUpdate, user: User) -> Concept:
    before = history.snapshot(concept, TRACKED_FIELDS)
    domains_before = sorted(domain.name for domain in concept.domains)

    if request.domain_ids is not None:
        concept.domains = _resolve_domains(db, request.domain_ids)

    domains_after = sorted(domain.name for domain in concept.domains)
    if domains_before != domains_after:
        history.record_changes(
            db,
            entity_type=HistoryEntityType.CONCEPT,
            entity_id=concept.id,
            before={"domains": domains_before},
            after={"domains": domains_after},
            changed_by=user,
        )

    history.record_changes(
        db,
        entity_type=HistoryEntityType.CONCEPT,
        entity_id=concept.id,
        before=before,
        after=history.snapshot(concept, TRACKED_FIELDS),
        changed_by=user,
    )
    db.commit()

    return concept


def deprecate(
    db: Session, concept: Concept, successor_id: uuid.UUID | None, user: User
) -> Concept:
    """Retire a concept, optionally pointing readers at its successor. → D7

    Deprecation is not a review status: the entries keep whatever status they
    had, and stay findable so that someone searching the old term is led to
    the new one instead of finding nothing.
    """
    if successor_id is not None:
        if successor_id == concept.id:
            raise SuccessorMustDiffer
        if db.get(Concept, successor_id) is None:
            raise UnknownSuccessor(str(successor_id))

    before = history.snapshot(concept, TRACKED_FIELDS)
    concept.lifecycle = ConceptLifecycle.DEPRECATED
    concept.superseded_by_id = successor_id

    history.record_changes(
        db,
        entity_type=HistoryEntityType.CONCEPT,
        entity_id=concept.id,
        before=before,
        after=history.snapshot(concept, TRACKED_FIELDS),
        changed_by=user,
    )
    db.commit()

    return concept


def reactivate(db: Session, concept: Concept, user: User) -> Concept:
    before = history.snapshot(concept, TRACKED_FIELDS)
    concept.lifecycle = ConceptLifecycle.ACTIVE
    # The check constraint only permits a successor on a deprecated concept.
    concept.superseded_by_id = None

    history.record_changes(
        db,
        entity_type=HistoryEntityType.CONCEPT,
        entity_id=concept.id,
        before=before,
        after=history.snapshot(concept, TRACKED_FIELDS),
        changed_by=user,
    )
    db.commit()

    return concept


def delete_concept(db: Session, concept: Concept) -> None:
    """Hard delete, Admin only.

    The change history survives: its rows carry no foreign key to the entity
    precisely so that they outlive it.
    """
    db.delete(concept)
    db.commit()


def _apply_filters(statement, filters: ConceptFilters):
    if filters.lifecycle is not None:
        statement = statement.where(Concept.lifecycle == filters.lifecycle)

    if filters.domain_ids:
        statement = statement.where(
            Concept.domains.any(Domain.id.in_(filters.domain_ids))
        )

    entry_conditions = []
    if filters.language:
        entry_conditions.append(TermEntry.language_code == filters.language.lower())
    if filters.statuses:
        entry_conditions.append(TermEntry.status.in_(filters.statuses))
    if filters.assignee_id is not None:
        entry_conditions.append(TermEntry.assignee_id == filters.assignee_id)
    if filters.query:
        # Both sides normalised, so `Grosse` finds `Große`. → D16
        pattern = f"%{normalise(filters.query)}%"
        entry_conditions.append(TermEntry.search_text.like(pattern))

    if entry_conditions:
        statement = statement.where(Concept.term_entries.any(*entry_conditions))

    if filters.missing_language:
        statement = statement.where(
            ~Concept.term_entries.any(
                TermEntry.language_code == filters.missing_language.lower()
            )
        )

    return statement


def list_concepts(db: Session, filters: ConceptFilters) -> tuple[list[Concept], int]:
    """One page of the term list, plus the total for the pager."""
    total = db.scalar(_apply_filters(select(func.count(Concept.id)), filters)) or 0

    statement = _apply_filters(select(Concept), filters)
    statement = (
        _with_relations(statement)
        .order_by(Concept.updated_at.desc())
        .limit(filters.limit)
        .offset(filters.offset)
    )

    return list(db.scalars(statement)), total


def list_domains(db: Session) -> list[Domain]:
    return list(db.scalars(select(Domain).order_by(Domain.name)))


def create_domain(db: Session, name: str) -> Domain:
    domain = Domain(name=name.strip())
    db.add(domain)
    db.commit()
    return domain
