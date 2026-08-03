"""Term entry request and response shapes."""

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EntryOrigin, TermStatus
from app.schemas.common import UtcDatetime, VersionedUpdate
from app.services.workflow import Action


class TermEntryCreate(BaseModel):
    language_code: str = Field(min_length=2, max_length=2)
    term: str = Field(min_length=1, max_length=500)
    #: Optional here, required to reach Approved. → D5
    definition: str | None = None
    synonyms: list[str] = Field(default_factory=list)
    nogo_alternatives: list[str] = Field(default_factory=list)
    context_example: str | None = None
    source: str | None = None
    notes: str | None = None
    origin: EntryOrigin = EntryOrigin.MANUAL


class TermEntryUpdate(VersionedUpdate):
    """Every field optional except the version; only what is sent gets changed.

    Status is not among them — it moves through the transition endpoint, so
    the workflow rules cannot be bypassed by a plain update.
    """

    term: str | None = Field(default=None, min_length=1, max_length=500)
    definition: str | None = None
    synonyms: list[str] | None = None
    nogo_alternatives: list[str] | None = None
    context_example: str | None = None
    source: str | None = None
    notes: str | None = None


class TermEntryRead(BaseModel):
    """A term entry as the API returns it.

    One schema for every role, with `notes` blanked out below the editorial
    roles rather than dropped: the response shape then matches what OpenAPI
    documents, and a null tells a viewer nothing about whether remarks exist.
    → D18
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    concept_id: uuid.UUID
    language_code: str
    term: str
    definition: str | None
    synonyms: list[str]
    nogo_alternatives: list[str]
    context_example: str | None
    source: str | None
    status: TermStatus
    origin: EntryOrigin
    assignee_id: uuid.UUID | None
    created_by_id: uuid.UUID
    #: Internal remarks. Null for anyone below the editorial roles. → D18
    notes: str | None
    created_at: UtcDatetime
    updated_at: UtcDatetime
    version: int


class TransitionRequest(BaseModel):
    action: Action
    #: Required for the two negative outcomes. → D6
    comment: str | None = None


class AssignRequest(BaseModel):
    """Null clears the assignment; omitting the field is not the same thing."""

    assignee_id: uuid.UUID | None


class ReviewCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    term_entry_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    transition: str | None
    created_at: UtcDatetime


class ChangeHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    field: str
    old_value: str | None
    new_value: str | None
    changed_by_id: uuid.UUID
    changed_at: UtcDatetime
