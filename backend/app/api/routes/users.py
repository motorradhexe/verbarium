"""Account management. Admin only. → D15"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, require_admin
from app.models.user import User
from app.schemas.auth import UserProfile
from app.schemas.user import UserCreateRequest, UserUpdateRequest
from app.services import users as user_service

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[UserProfile], summary="List accounts")
def list_users(db: DbSession) -> list[User]:
    return user_service.list_users(db)


@router.post(
    "",
    response_model=UserProfile,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
def create_user(request: UserCreateRequest, db: DbSession) -> User:
    try:
        return user_service.create_user(db, request)
    except user_service.EmailAlreadyTaken:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists",
        ) from None


@router.patch("/{user_id}", response_model=UserProfile, summary="Update an account")
def update_user(
    user_id: uuid.UUID,
    request: UserUpdateRequest,
    db: DbSession,
) -> User:
    user = user_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such account")

    try:
        return user_service.update_user(db, user, request)
    except user_service.LastAdminProtected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This is the last active Admin — promote another account first",
        ) from None
