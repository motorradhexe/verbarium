"""Login, logout, and the signed-in user."""

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentUser, DbSession, SessionToken
from app.core.config import get_settings
from app.core.security import verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, PasswordChangeRequest, UserProfile
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_lifetime_hours * 3600,
        httponly=True,
        # Lax rather than Strict: the cookie must survive following a link
        # into the application, which is how people arrive from a chat message
        # or an email about a term awaiting review.
        samesite="lax",
        secure=settings.session_cookie_secure,
        path="/",
    )


@router.post("/login", response_model=UserProfile, summary="Sign in")
def login(request: LoginRequest, response: Response, db: DbSession) -> User:
    user = auth_service.authenticate(db, request.email, request.password)

    if user is None:
        # Deliberately the same answer for an unknown address, a wrong
        # password, and a deactivated account.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    auth_service.purge_expired_sessions(db)
    _set_session_cookie(response, auth_service.create_session(db, user))

    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Sign out")
def logout(response: Response, db: DbSession, token: SessionToken) -> None:
    if token is not None:
        auth_service.end_session(db, token)

    response.delete_cookie(get_settings().session_cookie_name, path="/")


@router.get("/me", response_model=UserProfile, summary="The signed-in user")
def me(user: CurrentUser) -> User:
    return user


@router.post(
    "/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change your own password",
)
def change_password(
    request: PasswordChangeRequest,
    response: Response,
    db: DbSession,
    user: CurrentUser,
) -> None:
    if not verify_password(request.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Current password is incorrect",
        )

    # Ends every session, including this one — the caller signs in again.
    auth_service.change_password(db, user, request.new_password)
    response.delete_cookie(get_settings().session_cookie_name, path="/")
