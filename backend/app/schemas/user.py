"""Account management by an Admin."""

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import Role
from app.schemas.auth import NewPassword


class UserCreateRequest(BaseModel):
    """There is no self-registration — an Admin creates accounts. → D15"""

    email: EmailStr
    display_name: str = Field(min_length=1, max_length=200)
    password: NewPassword
    role: Role = Role.VIEWER


class UserUpdateRequest(BaseModel):
    """Every field optional; only what is sent gets changed."""

    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    role: Role | None = None
    is_active: bool | None = None
