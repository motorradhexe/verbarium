"""Concept request and response shapes."""

import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import ConceptLifecycle, TermStatus
from app.schemas.common import UtcDatetime
from app.schemas.term import TermEntryCreate, TermEntryRead


class DomainCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class DomainRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class ConceptCreate(BaseModel):
    """A concept and, optionally, its first entries.

    Entries can come along in the same call: a concept with no term is not
    something anyone wants to create on purpose.
    """

    domain_ids: list[uuid.UUID] = Field(default_factory=list)
    terms: list[TermEntryCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _one_entry_per_language(self) -> "ConceptCreate":
        codes = [entry.language_code for entry in self.terms]
        if len(codes) != len(set(codes)):
            raise ValueError("A concept can hold only one entry per language")
        return self


class ConceptUpdate(BaseModel):
    domain_ids: list[uuid.UUID] | None = None


class DeprecateRequest(BaseModel):
    """Retire a concept, optionally pointing at its successor. → D7"""

    superseded_by_id: uuid.UUID | None = None


class ConceptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lifecycle: ConceptLifecycle
    superseded_by_id: uuid.UUID | None
    domains: list[DomainRead]
    #: Derived from the entries, not stored: the least advanced language wins.
    #: None when the concept has no entries yet. → D1, D17
    status: TermStatus | None
    term_entries: list[TermEntryRead]
    created_by_id: uuid.UUID
    created_at: UtcDatetime
    updated_at: UtcDatetime
    version: int


class LanguageCell(BaseModel):
    """One language's state in the term list."""

    term: str
    status: TermStatus


class ConceptListItem(BaseModel):
    """One row of the term list: a concept with a column per language.

    Coverage is then visible at a glance — a language with no entry is simply
    absent from `languages`, which is what the gap filter keys off. → D12
    """

    id: uuid.UUID
    lifecycle: ConceptLifecycle
    status: TermStatus | None
    domains: list[DomainRead]
    languages: dict[str, LanguageCell]
    updated_at: UtcDatetime


class ConceptPage(BaseModel):
    items: list[ConceptListItem]
    total: int
    limit: int
    offset: int
