from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.corpus import get_problem
from app.db.session import get_db
from app.models.favorite import Favorite
from app.models.user import User
from app.schemas.favorite import FavoriteCreate, FavoriteOut, FavoriteUpdate

router = APIRouter(prefix="/favorites", tags=["favorites"])


def _hydrate(favorite: Favorite) -> FavoriteOut:
    problem = get_problem(favorite.problem_id)
    return FavoriteOut(
        id=favorite.id,
        problem_id=favorite.problem_id,
        status=favorite.status,
        plan=favorite.plan,
        task_progress=favorite.task_progress or {},
        created_at=favorite.created_at,
        updated_at=favorite.updated_at,
        title=problem.get("title") if problem else None,
        summary=problem.get("summary") if problem else None,
        source=problem.get("source") if problem else None,
        domain=problem.get("domain", []) if problem else [],
    )


@router.get("", response_model=list[FavoriteOut])
def list_favorites(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    favorites = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
        .all()
    )
    return [_hydrate(f) for f in favorites]


@router.post("", response_model=FavoriteOut, status_code=status.HTTP_201_CREATED)
def add_favorite(
    payload: FavoriteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id, Favorite.problem_id == payload.problem_id)
        .first()
    )
    if existing is not None:
        return _hydrate(existing)  # idempotent — already favorited

    favorite = Favorite(user_id=current_user.id, problem_id=payload.problem_id)
    db.add(favorite)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already favorited.")
    db.refresh(favorite)
    return _hydrate(favorite)


@router.patch("/{problem_id}", response_model=FavoriteOut)
def update_favorite(
    problem_id: str,
    payload: FavoriteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Partial update for status / generated plan / task checklist — every
    field is optional, only what's provided changes. Used by the frontend
    to save a freshly generated roadmap, flip a checklist item, or change
    a project's status, all as one small PATCH rather than resending
    everything.
    """
    favorite = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id, Favorite.problem_id == problem_id)
        .first()
    )
    if favorite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not favorited.")

    if payload.status is not None:
        favorite.status = payload.status
    if payload.plan is not None:
        favorite.plan = payload.plan
    if payload.task_progress is not None:
        favorite.task_progress = payload.task_progress

    db.commit()
    db.refresh(favorite)
    return _hydrate(favorite)


@router.delete("/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    favorite = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id, Favorite.problem_id == problem_id)
        .first()
    )
    if favorite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not favorited.")
    db.delete(favorite)
    db.commit()
