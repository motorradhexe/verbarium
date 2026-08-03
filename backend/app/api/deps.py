"""Shared FastAPI dependencies."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.enums import Role
from app.models.user import User
from app.services import auth as auth_service

NOT_AUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_token(request: Request) -> str | None:
    """The session token from the cookie, whatever the cookie is named.

    Read from the request rather than declared as a `Cookie` parameter,
    because FastAPI would take the name from the parameter and ignore
    `VERBARIUM_SESSION_COOKIE_NAME`.
    """
    return request.cookies.get(get_settings().session_cookie_name)


DbSession = Annotated[Session, Depends(get_db)]
SessionToken = Annotated[str | None, Depends(get_session_token)]


def get_current_user(db: DbSession, token: SessionToken) -> User:
    """The signed-in user, or 401."""
    if token is None:
        raise NOT_AUTHENTICATED

    session = auth_service.resolve_session(db, token)
    if session is None:
        raise NOT_AUTHENTICATED

    if not session.user.is_active:
        # Deactivation ends sessions, but a session that predates the change
        # must not survive on a stale read either.
        raise NOT_AUTHENTICATED

    return session.user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(minimum: Role):
    """Dependency factory: the signed-in user must hold at least `minimum`.

    Roles are cumulative — see `Role.rank`.
    """

    def dependency(user: CurrentUser) -> User:
        if not user.role.can_act_as(minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires the {minimum.value} role or higher",
            )
        return user

    return dependency


require_admin = require_role(Role.ADMIN)

AdminUser = Annotated[User, Depends(require_admin)]
