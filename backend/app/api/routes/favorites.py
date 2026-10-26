import logging
import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.corpus import get_problem, reset_cache
from app.db.session import get_db
from app.models.favorite import Favorite
from app.models.user import User
from app.schemas.favorite import FavoriteCreate, FavoriteOut, FavoriteUpdate
from app.services.pdf_builder import build_pdf
from app.services.pptx_builder import build_pptx
from scripts.enrich_resume_value import is_fully_scored

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/favorites", tags=["favorites"])

PPTX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
PDF_MEDIA_TYPE = "application/pdf"


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
        has_pptx=favorite.pptx_file is not None,
        has_pdf=favorite.pdf_file is not None,
    )


def _enrich_in_background(problem_id: str) -> None:
    """Runs scripts.enrich_resume_value.enrich_one() for a problem a user
    just saved — see add_favorite() below. Best-effort by design: this
    runs after the HTTP response has already gone out (via
    BackgroundTasks), so a Gemini failure or missing GEMINI_API_KEY here
    is only logged, never surfaced to the user — the favorite itself was
    already saved successfully either way, and the problem just stays
    unscored, same as it was before the save."""
    from scripts.enrich_resume_value import enrich_one

    try:
        if enrich_one(problem_id):
            # app/core/corpus.py caches problems.json per process — without
            # this, the freshly-written score wouldn't show up until the
            # app restarts.
            reset_cache()
    except Exception:
        logger.exception("background enrich_one(%r) failed", problem_id)


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
    background_tasks: BackgroundTasks,
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

    # Lazy resume-value enrichment: a user actually saving a problem
    # ("opened and then added to their system") is the trigger, not the
    # scheduled scrape job — see app/services/refresh_job.py's docstring
    # for why enrichment doesn't run automatically on every newly-scraped
    # problem. Only fires when the problem is missing any of the nine
    # score fields — not just when it has none at all, so a problem only
    # partially scored before a field was added still gets backfilled.
    problem = get_problem(payload.problem_id)
    if problem is not None and not is_fully_scored(problem):
        background_tasks.add_task(_enrich_in_background, payload.problem_id)

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
        # A new/regenerated roadmap invalidates any PPT/PDF cached for the
        # old one — see Favorite.pptx_file's docstring. Re-generated lazily
        # next time someone exports/views.
        favorite.pptx_file = None
        favorite.pptx_filename = None
        favorite.pdf_file = None
        favorite.pdf_filename = None
    if payload.task_progress is not None:
        favorite.task_progress = payload.task_progress

    db.commit()
    db.refresh(favorite)
    return _hydrate(favorite)


def _get_favorite_with_plan_or_404(problem_id: str, current_user: User, db: Session) -> Favorite:
    favorite = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id, Favorite.problem_id == problem_id)
        .first()
    )
    if favorite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not favorited.")
    if favorite.plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No roadmap generated for this project yet.")
    return favorite


def _export_filename(problem_id: str, favorite: Favorite, ext: str) -> str:
    problem = get_problem(problem_id) or {}
    title = problem.get("title") or favorite.plan.get("problem_understanding") or "Roadmap"
    slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").lower() or "roadmap"
    return problem, title, f"{slug}.{ext}"


@router.get("/{problem_id}/export-pptx")
def export_favorite_pptx(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Downloads this project's roadmap as a .pptx (the real, editable file —
    for opening in PowerPoint). Generated once and cached on the favorite
    row (see Favorite.pptx_file) so opening it again from My Projects,
    Problem Details, or the Roadmap page is instant and makes no repeat
    work, instead of regenerating/re-downloading a fresh copy every time.
    See GET .../view-pdf for the in-browser "View PPT" counterpart.
    """
    favorite = _get_favorite_with_plan_or_404(problem_id, current_user, db)

    if favorite.pptx_file is None:
        problem, title, filename = _export_filename(problem_id, favorite, "pptx")
        buffer = build_pptx(
            problem_title=title,
            problem_statement=problem.get("summary") or "",
            plan=favorite.plan,
            source=problem.get("source"),
            hackathon_name=problem.get("hackathon_name"),
        )
        favorite.pptx_file = buffer.getvalue()
        favorite.pptx_filename = filename
        db.commit()
        db.refresh(favorite)

    return StreamingResponse(
        iter([favorite.pptx_file]),
        media_type=PPTX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{favorite.pptx_filename}"'},
    )


@router.get("/{problem_id}/view-pdf")
def view_favorite_pdf(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Serves this project's roadmap as a .pdf for in-browser viewing (the
    "View PPT" button) — Content-Disposition: inline, not attachment, so
    the browser opens its own PDF viewer instead of downloading a file.
    Same real plan content as the .pptx, rendered through
    app/services/pdf_builder.py (browsers can't render .pptx natively, and
    this environment has no LibreOffice/PowerPoint for a true conversion).
    Generated once and cached on the favorite row (Favorite.pdf_file), same
    as the .pptx export above.
    """
    favorite = _get_favorite_with_plan_or_404(problem_id, current_user, db)

    if favorite.pdf_file is None:
        problem, title, filename = _export_filename(problem_id, favorite, "pdf")
        buffer = build_pdf(
            problem_title=title,
            problem_statement=problem.get("summary") or "",
            plan=favorite.plan,
            source=problem.get("source"),
            hackathon_name=problem.get("hackathon_name"),
        )
        favorite.pdf_file = buffer.getvalue()
        favorite.pdf_filename = filename
        db.commit()
        db.refresh(favorite)

    return StreamingResponse(
        iter([favorite.pdf_file]),
        media_type=PDF_MEDIA_TYPE,
        headers={"Content-Disposition": f'inline; filename="{favorite.pdf_filename}"'},
    )


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
