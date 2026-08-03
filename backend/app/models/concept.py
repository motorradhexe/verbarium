"""Concepts and domains.

A concept is the language-independent anchor holding all of its language
entries together. It carries no review status — that sits on the term entry,
one cycle per language. → D1
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Uuid,
)
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, enum_column, json_type, utcnow, uuid_pk
from app.models.enums import ConceptLifecycle

if TYPE_CHECKING:
    from app.models.term import TermEntry
    from app.models.user import User


concept_domains = Table(
    "concept_domains",
    Base.metadata,
    Column("concept_id", Uuid, ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True),
    Column("domain_id", Uuid, ForeignKey("domains.id", ondelete="CASCADE"), primary_key=True),
)


class Domain(Base):
    """A subject field such as Marketing, Development, or Legal.

    Its own entity rather than a string on the concept, so a domain can be
    renamed without touching every entry that uses it. → D9
    """

    __tablename__ = "domains"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def __repr__(self) -> str:
        return f"<Domain {self.name}>"


class Concept(Base):
    """The language-independent anchor for a set of term entries."""

    __tablename__ = "concepts"
    __table_args__ = (
        # A successor only makes sense for a retired concept, and nothing may
        # supersede itself.
        CheckConstraint(
            "superseded_by_id IS NULL OR lifecycle = 'deprecated'",
            name="successor_requires_deprecated",
        ),
        CheckConstraint(
            "superseded_by_id IS NULL OR superseded_by_id <> id",
            name="no_self_successor",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    lifecycle: Mapped[ConceptLifecycle] = mapped_column(
        enum_column(ConceptLifecycle, "concept_lifecycle"), default=ConceptLifecycle.ACTIVE
    )
    #: Where a deprecated concept's readers should go instead. → D7
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    #: Optimistic locking — a write based on a stale read is rejected. → D4
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    #: Workspace-defined fields; the configurable schema itself is v2.0.
    custom_fields: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(json_type()), default=dict, server_default="{}"
    )

    __mapper_args__ = {"version_id_col": version}

    superseded_by: Mapped["Concept | None"] = relationship(
        remote_side=[id], foreign_keys=[superseded_by_id]
    )
    created_by: Mapped["User"] = relationship()
    domains: Mapped[list[Domain]] = relationship(secondary=concept_domains, lazy="selectin")
    term_entries: Mapped[list["TermEntry"]] = relationship(
        back_populates="concept", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Concept {self.id} ({self.lifecycle})>"
