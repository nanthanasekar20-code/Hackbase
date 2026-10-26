from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas._datetime import assume_utc


class FavoriteCreate(BaseModel):
    problem_id: str


class FavoriteUpdate(BaseModel):
    """Partial update — only the fields set are changed (see PATCH /favorites/{problem_id})."""

    status: str | None = None
    plan: dict[str, Any] | None = None
    task_progress: dict[str, bool] | None = None


class FavoriteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    problem_id: str
    status: str
    plan: dict[str, Any] | None = None
    task_progress: dict[str, bool] = {}
    created_at: datetime
    updated_at: datetime
    # Hydrated from the JSON-backed problem corpus at read time (best
    # effort) so the frontend doesn't need a second lookup — None if the
    # problem_id no longer matches anything in the corpus.
    title: str | None = None
    summary: str | None = None
    source: str | None = None
    domain: list[str] = []
    # Whether a PPT/PDF has already been generated and cached for this
    # project's current plan — GET /favorites/{problem_id}/export-pptx (or
    # /view-pdf) serves that one instantly instead of rebuilding it; the
    # frontend uses this just to decide what label to show, not whether the
    # button works (it works either way, generating lazily on first use).
    has_pptx: bool = False
    has_pdf: bool = False

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _tz_aware(cls, value):
        return assume_utc(value)
