"""Workspace settings and the configured content languages."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow

SINGLETON_ID = 1


class WorkspaceSettings(Base):
    """Configuration of the one workspace this instance serves. → D8

    Enforced as a singleton: one row, fixed primary key. A second team runs a
    second instance rather than a second workspace.
    """

    __tablename__ = "workspace_settings"
    __table_args__ = (
        CheckConstraint(f"id = {SINGLETON_ID}", name="singleton"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=SINGLETON_ID)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    # The AI provider configuration belongs here too, but is deferred until the
    # BYOK key encryption is designed — keys must never reach the frontend.


class Language(Base):
    """A content language configured for this workspace. → D14

    Distinct from the interface language, which is a per-user preference and
    not stored here. Codes are validated against ISO 639-1 before they are
    written (`app.core.languages`), so the set cannot drift into regional tags
    like `de-DE`.

    A language in use cannot be deleted: `term_entries.language_code`
    references this table with `ON DELETE RESTRICT`, so the database refuses
    rather than cascading a delete through the termbase.
    """

    __tablename__ = "languages"
    __table_args__ = (
        CheckConstraint("length(code) = 2", name="code_is_two_letters"),
    )

    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    #: Column order in the term list.
    position: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
