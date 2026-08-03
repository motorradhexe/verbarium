"""Term entries: editing, the workflow, assignment, history."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, DbSession, require_role
from app.api.presenters import present_term
from app.models.enums import HistoryEntityType, Role, TermStatus
from app.models.term import TermEntry
from app.models.user import User
from app.schemas.term import (
    AssignRequest,
    ChangeHistoryRead,
    ReviewCommentRead,
    TermEntryRead,
    TermEntryUpdate,
    TransitionRequest,
)
from app.services import history as history_service
from app.services import terms as term_service
from app.services import workflow

router = APIRouter(prefix="/terms", tags=["terms"])

CanReview = Depends(require_role(Role.REVIEWER))
CanEdit = Depends(require_role(Role.EDITOR))
CanAdminister = Depends(require_role(Role.ADMIN))


def _load(db: DbSession, term_id: uuid.UUID) -> TermEntry:
    entry = term_service.get_term(db, term_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such term entry")
    return entry


def _may_edit(entry: TermEntry, user: User) -> bool:
    """Editors and above may edit anything.

    A Contributor may correct their own entry while it is still a Draft —
    otherwise submitting a proposal with a typo would be irreversible for the
    person who wrote it.
    """
    if user.role.can_act_as(Role.EDITOR):
        return True
    return entry.created_by_id == user.id and entry.status is TermStatus.DRAFT


@router.get("/{term_id}", response_model=TermEntryRead, summary="One term entry")
def read_term(term_id: uuid.UUID, db: DbSession, user: CurrentUser) -> TermEntryRead:
    return present_term(_load(db, term_id), user)


@router.patch("/{term_id}", response_model=TermEntryRead, summary="Update a term entry")
def update_term(
    term_id: uuid.UUID, request: TermEntryUpdate, db: DbSession, user: CurrentUser
) -> TermEntryRead:
    entry = _load(db, term_id)

    if not _may_edit(entry, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editing this entry requires the editor role or higher",
        )

    term_service.update_term(db, entry, request, user)

    return present_term(entry, user)


@router.delete(
    "/{term_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a term entry",
    dependencies=[CanEdit],
)
def delete_term(term_id: uuid.UUID, db: DbSession) -> None:
    term_service.delete_term(db, _load(db, term_id))


@router.post(
    "/{term_id}/transition",
    response_model=TermEntryRead,
    summary="Move an entry through the workflow",
)
def transition_term(
    term_id: uuid.UUID, request: TransitionRequest, db: DbSession, user: CurrentUser
) -> TermEntryRead:
    entry = _load(db, term_id)

    try:
        term_service.transition(db, entry, request.action, request.comment, user)
    except workflow.TransitionForbidden as refusal:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(refusal)) from None
    except workflow.TransitionNotAllowed as refusal:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(refusal)) from None
    except (workflow.CommentRequired, workflow.IncompleteEntry) as refusal:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(refusal)
        ) from None

    return present_term(entry, user)


@router.post(
    "/{term_id}/assignee",
    response_model=TermEntryRead,
    summary="Claim, hand over, or release an entry",
    dependencies=[CanReview],
)
def assign_term(
    term_id: uuid.UUID, request: AssignRequest, db: DbSession, user: CurrentUser
) -> TermEntryRead:
    entry = _load(db, term_id)

    try:
        term_service.assign(db, entry, request.assignee_id, user)
    except term_service.UnknownAssignee as unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No such active account: {unknown}",
        ) from None

    return present_term(entry, user)


@router.get(
    "/{term_id}/comments",
    response_model=list[ReviewCommentRead],
    summary="Review comments on this entry",
)
def term_comments(term_id: uuid.UUID, db: DbSession) -> list[ReviewCommentRead]:
    return term_service.comments_for(db, _load(db, term_id))


@router.get(
    "/{term_id}/history",
    response_model=list[ChangeHistoryRead],
    summary="What changed on this entry",
    dependencies=[CanEdit],
)
def term_history(term_id: uuid.UUID, db: DbSession) -> list[ChangeHistoryRead]:
    entry = _load(db, term_id)
    return history_service.history_for(db, HistoryEntityType.TERM_ENTRY, entry.id)
