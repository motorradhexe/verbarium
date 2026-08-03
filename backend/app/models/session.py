"""Server-side sessions. → D15

Sessions live in the database rather than in a signed cookie or a separate
store: a logout has to be able to end a session immediately, and keeping the
deployment to one container without Redis is worth more here than the read
saved per request.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, ensure_utc, utcnow, uuid_pk

if TYPE_CHECKING:
    from app.models.user import User


class UserSession(Base):
    """One signed-in session.

    Only the hash of the token is stored, so a database leak does not hand
    over usable sessions.
    """

    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    #: SHA-256 of the token the client holds. Unique, and the lookup key on
    #: every authenticated request.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship()

    def is_expired(self, now: datetime | None = None) -> bool:
        return (now or utcnow()) >= ensure_utc(self.expires_at)

    def __repr__(self) -> str:
        return f"<UserSession user={self.user_id} expires={self.expires_at:%Y-%m-%d}>"
