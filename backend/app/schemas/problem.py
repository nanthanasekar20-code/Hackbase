"""
Internal schemas for the data ingestion pipeline (scrape -> clean ->
normalize -> dedup -> processed corpus). These are distinct from the
API-facing schemas in app.schemas.query / app.schemas.plan — they exist to
validate records as they move through app/ingestion/*, before anything is
embedded or served over HTTP.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

# Keep in sync with the `source` column comment on app.models.hackathon.Hackathon.
VALID_SOURCES = {"sih", "devpost", "campus", "unstop", "hackerearth", "government", "article"}


class RawProblem(BaseModel):
    """Shape every scraper / curated-data loader must produce."""

    title: str
    description: str = ""
    organization: Optional[str] = None
    source: str
    hackathon_name: Optional[str] = None
    external_id: Optional[str] = None
    category: Optional[str] = None
    theme: Optional[str] = None
    url: Optional[str] = None
    fetched_at: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("title must not be blank")
        return v

    @field_validator("source")
    @classmethod
    def source_known(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if v not in VALID_SOURCES:
            raise ValueError(f"unknown source '{v}', expected one of {sorted(VALID_SOURCES)}")
        return v


class ProcessedProblem(BaseModel):
    """RawProblem after cleaning/normalization/dedup/heuristic tagging."""

    id: str
    title: str
    summary: str
    problem_statement: str
    organization: Optional[str] = None
    source: str
    hackathon_name: Optional[str] = None
    external_id: Optional[str] = None
    category: Optional[str] = None
    domain: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    difficulty: Optional[str] = None
    url: Optional[str] = None
    # Populated by the Gemini enrichment pass (scripts/enrich_resume_value.py)
    # — null until that's run for a given problem (batch, or lazily on save
    # via app/api/routes/favorites.py). All nine share one 0-10 scale; see
    # enrich_resume_value.py's PROMPT_TEMPLATE for exact definitions.
    # hardware_requirement_score is the one field where higher isn't
    # "better" — it just means more specialized hardware is needed.
    resume_value_score: Optional[float] = None
    industry_relevance_score: Optional[float] = None
    technical_depth_score: Optional[float] = None
    novelty_score: Optional[float] = None
    dataset_availability_score: Optional[float] = None
    hardware_requirement_score: Optional[float] = None
    competition_potential_score: Optional[float] = None
    social_impact_score: Optional[float] = None
    feasibility_score: Optional[float] = None
    # ISO date (YYYY-MM-DD) this problem's id was first seen in
    # data/processed/problems.json. Set once and preserved by id across
    # every rebuild (see scripts/build_corpus.py's _restore_first_seen_dates)
    # — never touched again after that, so it stays a stable "when did this
    # first show up" fact rather than a "last rebuilt" timestamp. Powers
    # the frontend's "New" badge (see app.schemas.query.RankedResult).
    first_seen_at: Optional[str] = None
