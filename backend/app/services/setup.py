"""First-run setup."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.languages import language_name
from app.core.security import hash_password
from app.models.enums import Role
from app.models.user import User
from app.models.workspace import Language, WorkspaceSettings
from app.schemas.setup import SetupRequest
from app.services.auth import normalise_email


class AlreadySetUp(Exception):
    """Raised when setup runs against an instance that already has an account."""


def is_complete(db: Session) -> bool:
    """Setup is done once an account exists.

    Keyed on users rather than on the settings row: an instance with a
    workspace name but no way to sign in is not usable, and the account is
    what the wizard exists to create.
    """
    return db.scalar(select(func.count()).select_from(User)) > 0


def run_setup(db: Session, request: SetupRequest) -> User:
    """Create the workspace, its languages, and the first Admin.

    All in one transaction: a partial setup would leave the instance in a
    state nothing else knows how to handle.
    """
    if is_complete(db):
        raise AlreadySetUp

    db.add(WorkspaceSettings(name=request.workspace_name))

    for position, choice in enumerate(request.languages):
        db.add(
            Language(
                code=choice.code,
                name=choice.name or language_name(choice.code),
                position=position,
            )
        )

    admin = User(
        email=normalise_email(request.admin_email),
        display_name=request.admin_display_name,
        password_hash=hash_password(request.admin_password),
        role=Role.ADMIN,
    )
    db.add(admin)

    db.commit()

    return admin
