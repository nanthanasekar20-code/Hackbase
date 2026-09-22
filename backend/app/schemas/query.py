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
    # Resume Value Score breakdown — populated by the Phase 2 enrichment
    # pass, not required to be present yet.
    resume_value_score: Optional[float] = None
    industry_relevance_score: Optional[float] = None
    technical_depth_score: Optional[float] = None


class QueryResponse(BaseModel):
    query: str
    results: list[RankedResult]
