"""First-run setup wizard.

Open without authentication by necessity — it runs before any account exists.
It closes itself the moment one does.
"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.models.user import User
from app.schemas.auth import UserProfile
from app.schemas.setup import SetupRequest, SetupStatus
from app.services import setup as setup_service

router = APIRouter(prefix="/setup", tags=["setup"])


@router.get("", response_model=SetupStatus, summary="Whether setup has run")
def status_(db: DbSession) -> SetupStatus:
    return SetupStatus(completed=setup_service.is_complete(db))


@router.post(
    "",
    response_model=UserProfile,
    status_code=status.HTTP_201_CREATED,
    summary="Create the workspace and its first Admin",
)
def run_setup(request: SetupRequest, db: DbSession) -> User:
    try:
        return setup_service.run_setup(db, request)
    except setup_service.AlreadySetUp:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This instance is already set up",
        ) from None
