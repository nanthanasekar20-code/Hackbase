from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import get_db
from app.models.user import User

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated — include 'Authorization: Bearer <token>'.",
        )
    try:
        email = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}") from exc

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists.")
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Same decoding as get_current_user, but never raises — returns None for
    a missing/invalid/expired token instead of 401ing. For endpoints like
    GET /search that must work identically for anonymous users and only
    add behavior (personalization) for a logged-in one — see
    app/api/routes/search.py.
    """
    if credentials is None:
        return None
    try:
        email = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        return None
    return db.query(User).filter(User.email == email).first()


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Same as get_current_user, plus requires role == "admin". 403 (not 401)
    — the caller IS authenticated, they just don't have permission.
    """
    if current_user.role != User.ROLE_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user
