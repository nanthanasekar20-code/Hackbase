"""
Response shapes for the non-RAG problem-browsing endpoints
(app/api/routes/problems.py: GET /problems/random and GET /problems) —
plain reads over data/processed/problems.json via
app.core.corpus.get_all_problems(), no vector search involved. Deliberately
separate from app.schemas.query.RankedResult: these aren't ranked against
a query, so there's no `score` field to fabricate one for.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class BrowseProblem(BaseModel):
    id: str
    title: str
    source: str
    hackathon_name: Optional[str] = None
    category: Optional[str] = None
    domain: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    difficulty: Optional[str] = None
    summary: str
    # Gemini enrichment scores (scripts/enrich_resume_value.py) — same
    # fields/scale/None-handling as app.schemas.query.RankedResult, kept in
    # sync by hand (these two schemas read from the same on-disk problem
    # records but serve different, independently-evolving endpoints).
    resume_value_score: Optional[float] = None
    industry_relevance_score: Optional[float] = None
    technical_depth_score: Optional[float] = None
    novelty_score: Optional[float] = None
    dataset_availability_score: Optional[float] = None
    hardware_requirement_score: Optional[float] = None
    competition_potential_score: Optional[float] = None
    social_impact_score: Optional[float] = None
    feasibility_score: Optional[float] = None
    first_seen_at: Optional[str] = None


class RandomProblemsResponse(BaseModel):
    problems: list[BrowseProblem]


class ProblemsPageResponse(BaseModel):
    page: int
    page_size: int
    total: int
    problems: list[BrowseProblem]
