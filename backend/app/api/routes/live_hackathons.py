from fastapi import APIRouter

from app.core.live_hackathons import get_live_hackathons
from app.schemas.live_hackathons import LiveHackathonsResponse

router = APIRouter()


@router.get("/live-hackathons", response_model=LiveHackathonsResponse)
def live_hackathons(source: str | None = None, search: str | None = None):
    """
    Hackathons currently open for registration, scraped separately from
    the problem-statement corpus (see scripts/run_live_hackathons.py).
    Just reads the refreshed JSON file — no database table, no live
    scrape per request.

    `source`/`search` are optional, additive filters for the full listing
    page (frontend/src/pages/LiveHackathons.jsx) — platform/source exact
    match and a case-insensitive title substring search. Neither is
    required: with no params, this returns the exact same payload as
    before they existed (the Home page teaser's call is unaffected).
    `per_source_counts` is always the real, UNFILTERED breakdown (it's
    what builds the source filter's own options/counts) — only
    `hackathons` and `count` reflect the active filter.
    """
    data = get_live_hackathons()
    if not source and not search:
        return data

    hackathons = data.get("hackathons", [])
    if source:
        hackathons = [h for h in hackathons if h.get("source") == source]
    if search:
        needle = search.lower()
        hackathons = [h for h in hackathons if needle in (h.get("title") or "").lower()]

    return {**data, "hackathons": hackathons, "count": len(hackathons)}
