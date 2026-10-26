from typing import Optional

from pydantic import BaseModel, Field


class LiveHackathon(BaseModel):
    title: str
    source: str
    url: str
    # Only present when the source made it trivial to grab (not every
    # scraper extracts one) — None rather than a fabricated/guessed date.
    deadline: Optional[str] = None
    fetched_at: Optional[str] = None


class LiveHackathonsResponse(BaseModel):
    updated_at: Optional[str] = None
    count: int = 0
    per_source_counts: dict[str, int] = Field(default_factory=dict)
    hackathons: list[LiveHackathon] = Field(default_factory=list)
