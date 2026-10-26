"""
Small shared reader for the JSON-backed live-hackathons feed
(data/processed/live_hackathons.json, see scripts/run_live_hackathons.py)
— completely separate from the problem-statement corpus
(app/core/corpus.py reads data/processed/problems.json instead). Loaded
once per process and cached in memory, same pattern as corpus.py; the
scheduled refresh job (app/services/live_hackathons_job.py) calls
reset_cache() after writing a fresh file so the next request picks it up
without needing a process restart.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

# app/core/live_hackathons.py -> parents[3] = <project_root>, matching
# the same resolution app/core/corpus.py uses.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "live_hackathons.json"

_EMPTY_PAYLOAD = {"updated_at": None, "count": 0, "per_source_counts": {}, "hackathons": []}

_cache: dict | None = None

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Matches the handful of real shapes the scrapers actually produce for
# `deadline` (see e.g. app/scrapers/live_devpost_scraper.py,
# live_mlh_scraper.py): "Oct 03, 2026", "Oct 03 - 31, 2026",
# "Oct 01 - Nov 12, 2026", "NOV 07 - 08" (no year at all). Group 1/2 are
# the start month/day, group 3 an optional second month (only present for
# a cross-month range), group 4 the end day, group 5 an optional year.
_DEADLINE_PATTERN = re.compile(
    r"([A-Za-z]{3,9})\s+(\d{1,2})\s*(?:-\s*(?:([A-Za-z]{3,9})\s+)?(\d{1,2}))?\s*(?:,\s*(\d{4}))?",
    re.IGNORECASE,
)


def _parse_deadline_end_date(deadline: str | None) -> date | None:
    """Best-effort end-of-submission-window date from a free-text
    `deadline` string, or None if it doesn't parse — a hackathon we can't
    confidently date is never treated as ended just because the text was
    unusual; silently hiding it would be worse than leaving it visible."""
    if not deadline:
        return None
    match = _DEADLINE_PATTERN.search(deadline)
    if not match:
        return None

    start_month, start_day, end_month, end_day, year_str = match.groups()
    month_name = (end_month or start_month)[:3].lower()
    month = _MONTHS.get(month_name)
    if month is None:
        return None
    try:
        day = int(end_day or start_day)
    except (TypeError, ValueError):
        return None

    today = datetime.now(timezone.utc).date()
    if year_str:
        year = int(year_str)
    else:
        # No year in the source text (MLH's shape) — assume this year,
        # unless that would already be well in the past, in which case a
        # freshly-scraped listing almost certainly meant next year.
        year = today.year
        try:
            if (today - date(year, month, day)).days > 60:
                year += 1
        except ValueError:
            return None

    try:
        return date(year, month, day)
    except ValueError:
        return None


def _has_clearly_ended(hackathon: dict) -> bool:
    end_date = _parse_deadline_end_date(hackathon.get("deadline"))
    if end_date is None:
        return False
    return end_date < datetime.now(timezone.utc).date()


def _load() -> dict:
    global _cache
    if _cache is None:
        if PROCESSED_PATH.exists():
            _cache = json.loads(PROCESSED_PATH.read_text(encoding="utf-8"))
        else:
            # No scrape has run yet — an honest empty feed, not fabricated
            # entries. The frontend shows a plain empty state for this.
            _cache = dict(_EMPTY_PAYLOAD)
    return _cache


def get_live_hackathons() -> dict:
    """
    The cached feed (see _load()), with anything whose own deadline text
    has clearly passed excluded — evaluated against the real wall-clock
    "now" on every call, not just at scrape time. This matters because the
    scheduled refresh (app/services/live_hackathons_job.py) only runs
    while the app process stays up; a hackathon that was genuinely open
    when last scraped can still end before the next refresh actually
    happens, and without this, it would keep showing as "open" until
    someone manually re-runs the scrape. Most sources don't capture a
    parseable deadline at all (see _parse_deadline_end_date) — those are
    left exactly as scraped, same as before this existed.
    """
    data = _load()
    hackathons = data.get("hackathons", [])
    still_open = [h for h in hackathons if not _has_clearly_ended(h)]
    if len(still_open) == len(hackathons):
        return data  # nothing excluded — identical to before this existed

    return {
        **data,
        "hackathons": still_open,
        "count": len(still_open),
        "per_source_counts": dict(Counter(h.get("source") for h in still_open if h.get("source"))),
    }


def reset_cache() -> None:
    """Called after scripts/run_live_hackathons.py writes a fresh file
    (see app/services/live_hackathons_job.py) so the next request reads
    the new data instead of serving a stale in-memory copy — also used by
    tests to force a re-read."""
    global _cache
    _cache = None
