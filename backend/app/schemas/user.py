from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

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
    """

    full_name: str | None = None
    email: EmailStr | None = None
    new_password: str | None = Field(default=None, min_length=8)
    current_password: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None = None
    role: str
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def _tz_aware(cls, value):
        return assume_utc(value)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
