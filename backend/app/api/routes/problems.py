"""
Non-RAG reads over the problem corpus — a genuinely random sample (for
Home's "Refresh" on Featured) and a flat paginated browse-all (for the
"Explore all" page). Both read app.core.corpus.get_all_problems()
directly, same simple-JSON-reader spirit as app/core/live_hackathons.py;
neither touches the vector index, Chroma, or app/rag/retriever.py — the
existing POST /search (app/api/routes/search.py) is still the only
RAG/semantic-ranked path, and is unaffected by anything here.
"""

from __future__ import annotations

import random

from fastapi import APIRouter, Query

from app.core.corpus import get_all_problems
from app.schemas.problem_browse import ProblemsPageResponse, RandomProblemsResponse

router = APIRouter()

MAX_RANDOM_COUNT = 24
MAX_PAGE_SIZE = 100


@router.get("/problems/random", response_model=RandomProblemsResponse)
def random_problems(count: int = Query(6, ge=1, le=MAX_RANDOM_COUNT)):
    """
    A genuinely reshuffled random sample, not a fixed/cached slice — each
    call draws fresh via random.sample, so clicking "Refresh" on Home's
    Featured section actually gets different problems rather than
    rerunning the same RAG query (see app/schemas/query.FEATURED_QUERY's
    use in the old flow this replaces).
    """
    pool = get_all_problems()
    sample = random.sample(pool, k=min(count, len(pool)))
    return RandomProblemsResponse(problems=sample)


@router.get("/problems", response_model=ProblemsPageResponse)
def list_problems(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    domain: str | None = None,
    source: str | None = None,
    category: str | None = None,
    difficulty: str | None = None,
):
    """Flat, paginated listing of the whole corpus — for a true browse-all
    page, as distinct from /discover's search-box-first RAG flow."""
    pool = get_all_problems()

    if domain:
        pool = [p for p in pool if domain in (p.get("domain") or [])]
    if source:
        pool = [p for p in pool if p.get("source") == source]
    if category:
        pool = [p for p in pool if p.get("category") == category]
    if difficulty:
        pool = [p for p in pool if p.get("difficulty") == difficulty]

    total = len(pool)
    start = (page - 1) * page_size
    page_items = pool[start : start + page_size]

    return ProblemsPageResponse(page=page, page_size=page_size, total=total, problems=page_items)
