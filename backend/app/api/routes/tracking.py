from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.core.tracking import TRACKED_EXPERIMENTS, list_runs
from app.models.user import User
from app.schemas.tracking import TrackingResponse

router = APIRouter()


@router.get("/tracking/runs", response_model=TrackingResponse)
def get_tracking_runs(limit: int = 20, current_user: User = Depends(require_admin)):
    """
    Real MLflow runs (see app.core.tracking) for the Planning Agent and
    Resume Value enrichment experiments, most recent first. Returns an
    empty run list per experiment if mlflow isn't installed or nothing has
    run yet — never fabricated placeholder data.

    Admin-only (not just any logged-in user, see app.api.deps.require_admin)
    — this is internal operational data (prompts, latencies, error messages
    from real Gemini calls), not something every account should see.
    """
    return TrackingResponse(
        experiments=[
            {"name": name, "runs": list_runs(name, limit=limit)}
            for name in TRACKED_EXPERIMENTS
        ]
    )
