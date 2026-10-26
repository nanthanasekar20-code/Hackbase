import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.email import EmailNotConfiguredError, EmailSendError, send_email
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserLogin,
    UserOut,
    UserUpdate,
    VerifyPasswordRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        # Deliberately identical error for "no such user" and "wrong
        # password" — don't leak which one it was.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")

    token = create_access_token(subject=user.email)
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Partial profile update. Changing email or password requires
    current_password — see UserUpdate's docstring for why.
    """
    wants_sensitive_change = payload.email is not None or payload.new_password is not None
    if wants_sensitive_change:
        if not payload.current_password or not verify_password(
            payload.current_password, current_user.hashed_password
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="current_password is required and must be correct to change email or password.",
            )

    if payload.full_name is not None:
        current_user.full_name = payload.full_name

    if payload.email is not None and payload.email != current_user.email:
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists."
            )
        current_user.email = payload.email

    if payload.new_password is not None:
        current_user.hashed_password = hash_password(payload.new_password)

    # Optional personalization — see UserUpdate's docstring for the
    # []/"" clear-sentinel convention. Neither requires current_password:
    # these aren't login credentials, so there's nothing a stolen session
    # token gains by changing them that it couldn't already do anyway.
    if payload.interests is not None:
        current_user.interests = payload.interests
    if payload.skill_level is not None:
        current_user.skill_level = payload.skill_level or None

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/verify-password", response_model=MessageResponse)
def verify_password_route(
    payload: VerifyPasswordRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Checks a password against the signed-in user's own hash without
    changing anything — lets the Profile page gate the "new password"
    fields behind a correct current password instead of showing them
    immediately.
    """
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password.")
    return MessageResponse(message="Password verified.")


_FORGOT_PASSWORD_GENERIC_MESSAGE = "If an account exists for that email, a reset link has been sent."


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Always returns the same generic message whether or not the email
    belongs to an account, so this can't be used to enumerate registered
    emails. Only sends a real email (via app/core/email.py) when one
    actually matches a user.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if user is not None:
        reset_token = create_password_reset_token(user.email)
        reset_link = f"{settings.frontend_base_url}/reset-password?token={reset_token}"
        body = (
            f"Hi{' ' + user.full_name if user.full_name else ''},\n\n"
            "Someone requested a password reset for your HackBase account. "
            f"If this was you, set a new password here (link expires in 30 minutes):\n\n{reset_link}\n\n"
            "If you didn't request this, you can ignore this email."
        )
        try:
            send_email(to=user.email, subject="Reset your HackBase password", body=body)
        except EmailNotConfiguredError as exc:
            # A real infra gap, not a per-email fact — safe to surface
            # since it doesn't depend on whether this email exists.
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except EmailSendError as exc:
            logger.exception("forgot_password: send_email failed")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return MessageResponse(message=_FORGOT_PASSWORD_GENERIC_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        email = decode_password_reset_token(payload.token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or has expired."
        ) from exc

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or has expired."
        )

    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return MessageResponse(message="Password updated. You can now log in with your new password.")
