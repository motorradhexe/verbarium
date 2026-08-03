"""Account management."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.enums import Role
from app.models.user import User
from app.schemas.user import UserCreateRequest, UserUpdateRequest
from app.services.auth import end_all_sessions_for, normalise_email


class EmailAlreadyTaken(Exception):
    pass


class LastAdminProtected(Exception):
    """Raised when a change would leave the workspace without an active Admin."""


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.display_name)))


def get_user(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def create_user(db: Session, request: UserCreateRequest) -> User:
    email = normalise_email(request.email)

    if db.scalar(select(User).where(User.email == email)) is not None:
        raise EmailAlreadyTaken

    user = User(
        email=email,
        display_name=request.display_name,
        password_hash=hash_password(request.password),
        role=request.role,
    )
    db.add(user)
    db.commit()

    return user


def _active_admin_count(db: Session, excluding: uuid.UUID) -> int:
    return len(
        [
            user
            for user in db.scalars(select(User).where(User.role == Role.ADMIN, User.is_active))
            if user.id != excluding
        ]
    )


def update_user(db: Session, user: User, request: UserUpdateRequest) -> User:
    """Apply the fields that were sent.

    Refuses to remove the last active Admin: an instance nobody can
    administer needs database access to recover, which is not a state to
    reach through the API by accident.
    """
    losing_admin = (request.role is not None and request.role != Role.ADMIN) or (
        request.is_active is False
    )
    if user.role == Role.ADMIN and user.is_active and losing_admin:
        if _active_admin_count(db, excluding=user.id) == 0:
            raise LastAdminProtected

    if request.display_name is not None:
        user.display_name = request.display_name
    if request.role is not None:
        user.role = request.role
    if request.is_active is not None:
        user.is_active = request.is_active

    db.commit()

    # A deactivated account must not keep working through an open session.
    if request.is_active is False:
        end_all_sessions_for(db, user)

    return user
