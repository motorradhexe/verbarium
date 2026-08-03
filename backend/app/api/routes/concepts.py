"""Concepts, their term entries, and the term list."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, require_role
from app.api.presenters import present_concept, present_list_item, present_term
from app.models.concept import Concept
from app.models.enums import ConceptLifecycle, HistoryEntityType, Role, TermStatus
from app.schemas.concept import (
    ConceptCreate,
    ConceptPage,
    ConceptRead,
    ConceptUpdate,
    DeprecateRequest,
)
from app.schemas.term import ChangeHistoryRead, TermEntryCreate, TermEntryRead
from app.services import concepts as concept_service
from app.services import history as history_service
from app.services import terms as term_service

router = APIRouter(prefix="/concepts", tags=["concepts"])

# Contributors submit proposals, so creating is open from that role up. The
# entries they create start as Draft and reach nothing further without the
# workflow. → REQUIREMENTS.md roles
CanContribute = Depends(require_role(Role.CONTRIBUTOR))
CanEdit = Depends(require_role(Role.EDITOR))
CanAdminister = Depends(require_role(Role.ADMIN))


SearchQuery = Annotated[
    str | None,
    Query(description="Text across terms, definitions, synonyms, and NoGo alternatives"),
]
LanguageFilter = Annotated[
    str | None, Query(description="Only concepts that have an entry in this language")
]
MissingLanguageFilter = Annotated[
    str | None,
    Query(description="Only concepts that lack an entry in this language — the gap filter"),
]
StatusFilter = Annotated[list[TermStatus] | None, Query(alias="status")]
DomainFilter = Annotated[list[uuid.UUID] | None, Query()]
AssigneeFilter = Annotated[uuid.UUID | None, Query()]
LifecycleFilter = Annotated[ConceptLifecycle | None, Query()]
PageLimit = Annotated[int, Query(ge=1, le=200)]
PageOffset = Annotated[int, Query(ge=0)]


def _load(db: DbSession, concept_id: uuid.UUID) -> Concept:
    concept = concept_service.get_concept(db, concept_id)
    if concept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such concept")
    return concept


@router.get("", response_model=ConceptPage, summary="The term list")
def list_concepts(
    db: DbSession,
    user: CurrentUser,
    query: SearchQuery = None,
    language: LanguageFilter = None,
    missing_language: MissingLanguageFilter = None,
    status_: StatusFilter = None,
    domain_id: DomainFilter = None,
    assignee_id: AssigneeFilter = None,
    lifecycle: LifecycleFilter = None,
    limit: PageLimit = 50,
    offset: PageOffset = 0,
) -> ConceptPage:
    filters = concept_service.ConceptFilters(
        query=query,
        language=language,
        missing_language=missing_language,
        statuses=status_ or [],
        domain_ids=domain_id or [],
        assignee_id=assignee_id,
        lifecycle=lifecycle,
        limit=limit,
        offset=offset,
    )
    items, total = concept_service.list_concepts(db, filters)

    return ConceptPage(
        items=[present_list_item(concept) for concept in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=ConceptRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a concept",
    dependencies=[CanContribute],
)
def create_concept(request: ConceptCreate, db: DbSession, user: CurrentUser) -> ConceptRead:
    try:
        concept = concept_service.create_concept(db, request, user)
    except concept_service.UnknownDomain as unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No such domain: {unknown}",
        ) from None
    except term_service.UnknownLanguage as unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{unknown} is not a configured content language",
        ) from None

    return present_concept(concept, user)


@router.get("/{concept_id}", response_model=ConceptRead, summary="One concept")
def read_concept(concept_id: uuid.UUID, db: DbSession, user: CurrentUser) -> ConceptRead:
    return present_concept(_load(db, concept_id), user)


@router.patch(
    "/{concept_id}",
    response_model=ConceptRead,
    summary="Update a concept",
    dependencies=[CanEdit],
)
def update_concept(
    concept_id: uuid.UUID, request: ConceptUpdate, db: DbSession, user: CurrentUser
) -> ConceptRead:
    concept = _load(db, concept_id)
    try:
        concept_service.update_concept(db, concept, request, user)
    except concept_service.UnknownDomain as unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No such domain: {unknown}",
        ) from None

    return present_concept(concept, user)


@router.post(
    "/{concept_id}/deprecate",
    response_model=ConceptRead,
    summary="Retire a concept",
    dependencies=[CanEdit],
)
def deprecate_concept(
    concept_id: uuid.UUID, request: DeprecateRequest, db: DbSession, user: CurrentUser
) -> ConceptRead:
    concept = _load(db, concept_id)
    try:
        concept_service.deprecate(db, concept, request.superseded_by_id, user)
    except concept_service.SuccessorMustDiffer:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A concept cannot supersede itself",
        ) from None
    except concept_service.UnknownSuccessor as unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No such successor concept: {unknown}",
        ) from None

    return present_concept(concept, user)


@router.post(
    "/{concept_id}/reactivate",
    response_model=ConceptRead,
    summary="Put a retired concept back in use",
    dependencies=[CanEdit],
)
def reactivate_concept(concept_id: uuid.UUID, db: DbSession, user: CurrentUser) -> ConceptRead:
    concept = _load(db, concept_id)
    concept_service.reactivate(db, concept, user)
    return present_concept(concept, user)


@router.delete(
    "/{concept_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a concept and its entries",
    dependencies=[CanAdminister],
)
def delete_concept(concept_id: uuid.UUID, db: DbSession) -> None:
    concept_service.delete_concept(db, _load(db, concept_id))


@router.post(
    "/{concept_id}/terms",
    response_model=TermEntryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a language entry",
    dependencies=[CanContribute],
)
def add_term(
    concept_id: uuid.UUID, request: TermEntryCreate, db: DbSession, user: CurrentUser
) -> TermEntryRead:
    concept = _load(db, concept_id)
    try:
        entry = term_service.create_term(db, concept, request, user)
    except term_service.UnknownLanguage as unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{unknown} is not a configured content language",
        ) from None
    except term_service.LanguageAlreadyPresent as present:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This concept already has a {present} entry",
        ) from None

    return present_term(entry, user)


@router.get(
    "/{concept_id}/history",
    response_model=list[ChangeHistoryRead],
    summary="What changed on this concept",
    dependencies=[CanEdit],
)
def concept_history(concept_id: uuid.UUID, db: DbSession) -> list[ChangeHistoryRead]:
    concept = _load(db, concept_id)
    return history_service.history_for(db, HistoryEntityType.CONCEPT, concept.id)
