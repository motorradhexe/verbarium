"""User accounts."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, enum_column, utcnow, uuid_pk
from app.models.enums import Role


class User(Base):
    """A local account. → D15

    Authentication is by session cookie against a password hashed with
    Argon2id; accounts are created by an Admin, there is no self-registration.

    External identity providers stay addable without touching existing data:
    that needs nullable `issuer` and `subject` columns plus a callback route,
    at which point `password_hash` becomes nullable for those accounts.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    #: Login. Stored lowercase — the service layer normalises before writing,
    #: because case-insensitive uniqueness is not portable between the two
    #: supported databases.
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(enum_column(Role, "role"), default=Role.VIEWER)
    #: Deactivated instead of deleted: entries reference their author, and the
    #: change history is worth more than the row.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
