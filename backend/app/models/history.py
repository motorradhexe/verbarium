"""Change history and review comments.

Two separate records for two separate jobs: the history is written
automatically and answers *what* changed, the comments are written by people
and answer *why*. → D6
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, enum_column, utcnow, uuid_pk
from app.models.enums import HistoryEntityType, ReviewTransition

if TYPE_CHECKING:
    from app.models.term import TermEntry
    from app.models.user import User


class ChangeHistoryEntry(Base):
    """One recorded field change on a concept or a term entry.

    Append-only and read-only to every role; visible to Editors, Reviewers,
    Approvers, and Admins.

    `entity_id` carries no foreign key because it points at one of two tables.
    The trade-off is deliberate: the history has to outlive the row it
    describes, so a cascade from the entity would defeat its purpose.
    """

    __tablename__ = "change_history"
    __table_args__ = (
        Index("ix_change_history_entity", "entity_type", "entity_id", "changed_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    entity_type: Mapped[HistoryEntityType] = mapped_column(
        enum_column(HistoryEntityType, "history_entity_type")
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    field: Mapped[str] = mapped_column(String(100))
    #: Rendered as text regardless of the column's type, so one table can
    #: record changes to strings, lists, and JSON alike.
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    changed_by: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<ChangeHistoryEntry {self.entity_type}.{self.field}>"


class ReviewComment(Base):
    """A reviewer's reasoning, attached to a term entry.

    Mandatory when requesting changes or rejecting — enforced at the workflow
    transition, since the column cannot know which transition it accompanies.
    """

    __tablename__ = "review_comments"
    __table_args__ = (
        Index("ix_review_comments_term_entry_id_created_at", "term_entry_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    term_entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("term_entries.id", ondelete="CASCADE")
    )
    author_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"))
    body: Mapped[str] = mapped_column(Text)
    #: The workflow step this comment accompanied, if any. A plain remark
    #: leaves it null.
    transition: Mapped[ReviewTransition | None] = mapped_column(
        enum_column(ReviewTransition, "review_transition"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    term_entry: Mapped["TermEntry"] = relationship()
    author: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<ReviewComment on {self.term_entry_id}>"
