"""First-run setup wizard."""

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.languages import ISO_639_1
from app.schemas.auth import NewPassword


class SetupStatus(BaseModel):
    completed: bool


class LanguageChoice(BaseModel):
    code: str = Field(description="ISO 639-1 code, e.g. `de`")
    name: str | None = Field(
        default=None, description="Display name; defaults to the ISO 639-1 English name"
    )

    @field_validator("code")
    @classmethod
    def _known_language(cls, value: str) -> str:
        normalised = value.strip().lower()
        if normalised not in ISO_639_1:
            raise ValueError(f"{value!r} is not an ISO 639-1 language code")
        return normalised


class SetupRequest(BaseModel):
    """Everything the first run needs, in one call.

    Workspace name, content languages, and the initial Admin account are
    created together: a half-configured instance with an admin but no
    languages would be a state the rest of the application has to handle.
    """

    workspace_name: str = Field(min_length=1, max_length=200)
    languages: list[LanguageChoice] = Field(min_length=1)
    admin_email: EmailStr
    admin_display_name: str = Field(min_length=1, max_length=200)
    admin_password: NewPassword

    @field_validator("languages")
    @classmethod
    def _no_duplicates(cls, value: list[LanguageChoice]) -> list[LanguageChoice]:
        codes = [language.code for language in value]
        if len(codes) != len(set(codes)):
            raise ValueError("The same language is listed more than once")
        return value
