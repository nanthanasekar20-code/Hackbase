from typing import Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    # Optional filter to one taxonomy domain (see app.core.taxonomy.DOMAINS),
    # e.g. "Healthcare". Ignored by agents until Phase 4 wires it through.
    domain: Optional[str] = None


class RankedResult(BaseModel):
    # Stable id for this problem (see app.utils.ids / ingestion pipeline).
    # Optional for now so existing stub agents that don't set it don't break.
    id: Optional[str] = None
    title: str
    source: str
    # Distinct from `source` (the platform/site, e.g. "sih") — the specific
    # event name, e.g. "Smart India Hackathon 2025".
    hackathon_name: Optional[str] = None
    domain: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    difficulty: Optional[str] = None
    summary: str
    score: float
    # Gemini enrichment scores (scripts/enrich_resume_value.py) — all nine
    # share one 0-10 scale, None until that problem's been enriched (batch
    # or lazy-on-save). hardware_requirement_score is the one field where
    # higher isn't "better", just "needs more specialized hardware".
    resume_value_score: Optional[float] = None
    industry_relevance_score: Optional[float] = None
    technical_depth_score: Optional[float] = None
    novelty_score: Optional[float] = None
    dataset_availability_score: Optional[float] = None
    hardware_requirement_score: Optional[float] = None
    competition_potential_score: Optional[float] = None
    social_impact_score: Optional[float] = None
    feasibility_score: Optional[float] = None
    # ISO date this problem was first seen (see app.schemas.problem
    # .ProcessedProblem.first_seen_at). Optional/None for any older record
    # indexed before this field existed — the frontend only renders a
    # "New" badge when it's actually present and recent, never fabricates
    # recency for a problem that doesn't carry the field yet.
    first_seen_at: Optional[str] = None


class QueryResponse(BaseModel):
    query: str
    results: list[RankedResult]
