"""Authentication and session handling. → D15"""

from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import get_settings
from app.db.base import utcnow
from app.models.session import UserSession
from app.models.user import User


def normalise_email(email: str) -> str:
    """Lowercase, because uniqueness is enforced by a plain unique index.

    Case-insensitive uniqueness is not portable between the two supported
    databases — PostgreSQL would need `citext` or a functional index, SQLite
    `COLLATE NOCASE` — so addresses are normalised before they are stored.
    """
    return email.strip().lower()


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Return the user for valid credentials, otherwise None.

    Never distinguishes "no such address" from "wrong password", neither in
    its result nor in how long it takes.
    """
    user = db.scalar(select(User).where(User.email == normalise_email(email)))

    if user is None:
        security.spend_dummy_verification()
        return None

    if not security.verify_password(password, user.password_hash):
        return None

    if not user.is_active:
        return None

    if security.needs_rehash(user.password_hash):
        user.password_hash = security.hash_password(password)
        db.commit()

    return user


def create_session(db: Session, user: User) -> str:
    """Open a session and return the token for the client to store.

    The token is returned once and never stored — only its hash is.
    """
    settings = get_settings()
    token = security.generate_session_token()

    db.add(
        UserSession(
            token_hash=security.hash_session_token(token),
            user_id=user.id,
            expires_at=utcnow() + timedelta(hours=settings.session_lifetime_hours),
        )
    )
    db.commit()

    return token


def resolve_session(db: Session, token: str) -> UserSession | None:
    """Look up a live session, deleting it if it has expired."""
    session = db.scalar(
        select(UserSession).where(UserSession.token_hash == security.hash_session_token(token))
    )

    if session is None:
        return None

    if session.is_expired():
        db.delete(session)
        db.commit()
        return None

    session.last_seen_at = utcnow()
    db.commit()

    return session


def end_session(db: Session, token: str) -> None:
    """Log out. Silent when the token is unknown — the outcome is the same."""
    db.execute(
        delete(UserSession).where(UserSession.token_hash == security.hash_session_token(token))
    )
    db.commit()


def end_all_sessions_for(db: Session, user: User) -> None:
    """Used when a password changes or an account is deactivated."""
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    db.commit()


def purge_expired_sessions(db: Session) -> int:
    """Housekeeping, run on login rather than as a scheduled job."""
    result = db.execute(delete(UserSession).where(UserSession.expires_at < utcnow()))
    db.commit()
    return result.rowcount or 0


def change_password(db: Session, user: User, new_password: str) -> None:
    """Set a new password and invalidate every existing session.

    Changing a password is how someone reacts to a suspected compromise, so
    it has to log out whoever else is signed in as that account.
    """
    user.password_hash = security.hash_password(new_password)
    db.commit()
    end_all_sessions_for(db, user)
