"""Turning models into the shape a given role may see.

Kept in one place so that field-level visibility is a single decision rather
than something each route repeats and eventually gets wrong.
"""

from app.models.concept import Concept
from app.models.enums import Role
from app.models.term import TermEntry
from app.models.user import User
from app.schemas.concept import ConceptListItem, ConceptRead, LanguageCell
from app.schemas.term import TermEntryRead
from app.services.workflow import rollup_status

#: From this role upward, internal notes are visible. Under D10 everyone can
#: see entries in progress, which would otherwise expose remarks written for
#: the editorial team. → D18
NOTES_VISIBLE_FROM = Role.EDITOR


def may_see_notes(user: User) -> bool:
    return user.role.can_act_as(NOTES_VISIBLE_FROM)


def present_term(entry: TermEntry, user: User) -> TermEntryRead:
    """One schema for every role, with `notes` blanked out below Editor.

    Blanked rather than omitted: a response whose keys depend on the caller's
    role would not match what OpenAPI documents, and FastAPI filters the
    response through the declared model anyway.
    """
    schema = TermEntryRead.model_validate(entry)

    if not may_see_notes(user):
        schema.notes = None

    return schema


def present_concept(concept: Concept, user: User) -> ConceptRead:
    return ConceptRead.model_validate(
        {
            "id": concept.id,
            "lifecycle": concept.lifecycle,
            "superseded_by_id": concept.superseded_by_id,
            "domains": concept.domains,
            # Derived, not stored: the least advanced language wins. → D1, D17
            "status": rollup_status(concept.term_entries),
            "term_entries": [present_term(entry, user) for entry in concept.term_entries],
            "created_by_id": concept.created_by_id,
            "created_at": concept.created_at,
            "updated_at": concept.updated_at,
            "version": concept.version,
        }
    )


def present_list_item(concept: Concept) -> ConceptListItem:
    """One row of the term list: a column per language. → D12

    Carries no notes at any role — the list is an overview, and the detail
    view is where the full entry lives.
    """
    return ConceptListItem(
        id=concept.id,
        lifecycle=concept.lifecycle,
        status=rollup_status(concept.term_entries),
        domains=concept.domains,
        languages={
            entry.language_code: LanguageCell(term=entry.term, status=entry.status)
            for entry in concept.term_entries
        },
        updated_at=concept.updated_at,
    )
