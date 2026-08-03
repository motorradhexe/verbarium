"""Request and response shapes for authentication."""

import uuid
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr

from app.core.config import get_settings
from app.models.enums import Role
from app.schemas.common import UtcDatetime


def _long_enough(value: str) -> str:
    minimum = get_settings().min_password_length
    if len(value) < minimum:
        raise ValueError(f"Password must be at least {minimum} characters long")
    return value


#: A password being chosen. Checked at validation time rather than through
#: `Field(min_length=...)` so the configured minimum applies without a restart.
NewPassword = Annotated[str, AfterValidator(_long_enough)]


class LoginRequest(BaseModel):
    email: EmailStr
    #: No minimum here: an existing password is being checked, not chosen, and
    #: a length rule would lock out accounts after the policy tightens.
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: NewPassword


class UserProfile(BaseModel):
    """A user as the API returns it — never carries the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str
    role: Role
    is_active: bool
    created_at: UtcDatetime
