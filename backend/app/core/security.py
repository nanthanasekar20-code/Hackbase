"""
Password hashing (bcrypt, used directly rather than through passlib — the
passlib+bcrypt combination has a well-known version-compatibility trap
with modern bcrypt releases) and JWT access-token creation/verification.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        # Malformed hash (shouldn't happen for anything we wrote ourselves).
        return False


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


class InvalidTokenError(Exception):
    pass


def decode_access_token(token: str) -> str:
    """Returns the token's `sub` claim (the user's email) or raises InvalidTokenError."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("token missing 'sub' claim")
    return subject


PASSWORD_RESET_PURPOSE = "password_reset"
PASSWORD_RESET_EXPIRE_MINUTES = 30


def create_password_reset_token(email: str) -> str:
    """
    A short-lived JWT carrying a `purpose` claim so it can't be reused as a
    normal access token (decode_access_token doesn't check `purpose`, so a
    reset token would otherwise also work as a login session token) and a
    normal access token can't be used to reset a password (reset-password
    checks `purpose` explicitly). Stateless by design — no extra DB table —
    since expiry alone (30 min) is enough for this app's threat model.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES)
    payload = {"sub": email, "purpose": PASSWORD_RESET_PURPOSE, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_password_reset_token(token: str) -> str:
    """Returns the reset token's subject email, or raises InvalidTokenError."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    if payload.get("purpose") != PASSWORD_RESET_PURPOSE:
        raise InvalidTokenError("token is not a password-reset token")
    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("token missing 'sub' claim")
    return subject
