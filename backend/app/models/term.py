"""Term entries — one per concept and language."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, enum_column, json_type, utcnow, uuid_pk
from app.models.enums import EntryOrigin, TermStatus

if TYPE_CHECKING:
    from app.models.concept import Concept
    from app.models.user import User


class TermEntry(Base):
    """One language's view of a concept, with its own review status.

    The review cycle runs per language: a reviewer who reads German can
    approve the German entry without vouching for the English one, and the
    concept shows the roll-up. → D1
    """

    __tablename__ = "term_entries"
    __table_args__ = (
        UniqueConstraint("concept_id", "language_code", name="one_entry_per_language"),
        # The review queue filters on these three.
        Index("ix_term_entries_status_language", "status", "language_code"),
        Index("ix_term_entries_assignee_id", "assignee_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    concept_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("concepts.id", ondelete="CASCADE")
    )
    #: RESTRICT: a configured language that is still in use cannot be removed
    #: without dealing with its entries first. → D14
    language_code: Mapped[str] = mapped_column(
        String(2), ForeignKey("languages.code", ondelete="RESTRICT")
    )

    term: Mapped[str] = mapped_column(String(500))
    #: Nullable on purpose: required to reach Approved, not to create an entry,
    #: so quick proposals and AI candidates without a definition are possible.
    #: Enforced at the workflow transition, not by the column. → D5
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    synonyms: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(json_type()), default=list, server_default="[]"
    )
    nogo_alternatives: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(json_type()), default=list, server_default="[]"
    )
    context_example: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Internal remarks. Visibility is still open: under D10 every role can see
    #: entries in progress, which would expose these unless the API restricts
    #: the field to the editorial roles.
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[TermStatus] = mapped_column(
        enum_column(TermStatus, "term_status"), default=TermStatus.DRAFT
    )
    #: Who is handling this entry — without it the review queue is an
    #: undifferentiated pile. → D2
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    #: Not a status, so an entry stays identifiable as an AI suggestion or an
    #: import after it moves through the workflow. → D3
    origin: Mapped[EntryOrigin] = mapped_column(
        enum_column(EntryOrigin, "entry_origin"), default=EntryOrigin.MANUAL
    )

    created_by_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    custom_fields: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(json_type()), default=dict, server_default="{}"
    )

    __mapper_args__ = {"version_id_col": version}

    concept: Mapped["Concept"] = relationship(back_populates="term_entries")
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assignee_id])
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])

    def __repr__(self) -> str:
        return f"<TermEntry {self.language_code}:{self.term} ({self.status})>"
