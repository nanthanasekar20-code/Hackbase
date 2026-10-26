from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.taxonomy import DOMAINS, SKILL_LEVELS
from app.schemas._datetime import assume_utc


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """
    Partial profile update — only fields that are set change (same
    None-means-unchanged pattern as FavoriteUpdate). Changing `email` or
    `new_password` requires `current_password` to also be set and correct
    — a stolen session token alone shouldn't be enough to take over the
    account's login credentials.

    interests/skill_level are optional personalization (see
    app.models.user.User) — entirely opt-in, never required anywhere in
    signup or first use. Clearing them back out needs its own sentinel
    since None already means "don't touch": interests=[] clears (an empty
    list was never ambiguous with "omitted" to begin with), and
    skill_level="" clears skill_level specifically (stored as a real NULL)
    since "" would otherwise be indistinguishable from "wasn't sent".
    """

    full_name: str | None = None
    email: EmailStr | None = None
    new_password: str | None = Field(default=None, min_length=8)
    current_password: str | None = None
    interests: list[str] | None = None
    skill_level: str | None = None

    @field_validator("interests")
    @classmethod
    def _interests_in_taxonomy(cls, value):
        if value is None:
            return value
        invalid = [v for v in value if v not in DOMAINS]
        if invalid:
            raise ValueError(f"Unknown interest(s): {invalid!r}. Must be one of {DOMAINS}.")
        return value

    @field_validator("skill_level")
    @classmethod
    def _skill_level_in_vocabulary(cls, value):
        if value is None or value == "":
            return value  # "" is the explicit clear sentinel, not a real level
        if value not in SKILL_LEVELS:
            raise ValueError(f"Unknown skill_level: {value!r}. Must be one of {SKILL_LEVELS}.")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None = None
    role: str
    created_at: datetime
    # Optional personalization — see UserUpdate's docstring. interests
    # defaults to [] (never None) so the frontend doesn't need a null
    # check on top of an empty-list check for "nothing set yet".
    interests: list[str] = []
    skill_level: str | None = None

    @field_validator("created_at", mode="before")
    @classmethod
    def _tz_aware(cls, value):
        return assume_utc(value)

    @field_validator("interests", mode="before")
    @classmethod
    def _interests_default(cls, value):
        return value or []


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VerifyPasswordRequest(BaseModel):
    current_password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class MessageResponse(BaseModel):
    message: str
