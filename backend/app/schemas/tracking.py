from typing import Optional

from pydantic import BaseModel, Field


class TrackedRun(BaseModel):
    run_id: str
    status: str
    start_time_ms: int
    params: dict[str, str] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    error: Optional[str] = None


class TrackedExperiment(BaseModel):
    name: str
    runs: list[TrackedRun]


class TrackingResponse(BaseModel):
    experiments: list[TrackedExperiment]
