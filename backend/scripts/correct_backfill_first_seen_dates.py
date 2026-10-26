"""
One-time, idempotent correction for scripts/backfill_first_seen.py's
output — NOT a change to how first_seen_at normally works, just fixing
the side effect of that one migration.

Why this exists: backfill_first_seen.py stamped every pre-existing
problem's first_seen_at with "today" as a neutral placeholder (we don't
actually know when most of these were really first scraped) — it says so
in its own docstring, and that's the right call for a one-time migration
with no real data to fall back on. But ProblemCard.jsx's "New" badge
shows for anything within NEW_BADGE_DAYS (7) days of first_seen_at, so
that entire backfilled batch currently reads as "new" — a few days after
the migration ran, practically the whole corpus still shows "New"
alongside genuinely-new scrapes, which defeats the badge's purpose.

This finds the backfill's actual stamped date by reading it from the
data itself — the backfill set the exact same date on every problem it
touched, so whichever single date is overwhelmingly dominant across the
corpus *is* that run's date (checked below: it must account for at least
half of all problems, so this can't misfire on an ordinary day where
several genuinely-new scrapes just happen to share a date) — never a
hardcoded guess. Every problem stamped with that exact date gets moved to
30 days before today: safely outside the New-badge window, while
honestly NOT pretending to know any of their real discovery dates (a
fabricated spread of distinct "real-looking" dates would be worse than
one honest unknown-but-old date). Anything with a different
first_seen_at (genuinely added after the original backfill ran) is left
completely untouched.

Idempotent: once the backfill-date problems have been moved, that date
is no longer within the New-badge window, so a second run finds nothing
within NEW_BADGE_DAYS to correct and exits as a no-op — safe to run more
than once, same guarantee backfill_first_seen.py itself makes.

Run as: python scripts/correct_backfill_first_seen_dates.py
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_PATH = ROOT / "data" / "processed" / "problems.json"

# Must match frontend/src/components/problem/ProblemCard.jsx's
# NEW_BADGE_DAYS — this script's whole job is fixing problems that
# currently fall inside that window for the wrong reason.
NEW_BADGE_DAYS = 7
# How far back to move corrected problems — safely past NEW_BADGE_DAYS
# with margin, so this doesn't need re-running again in a few days.
CORRECTED_AGE_DAYS = 30
# The backfill date must account for at least this fraction of all
# problems to be treated as "obviously a bulk stamp" rather than a
# handful of genuinely-new problems that happen to share a date.
MIN_MAJORITY_FRACTION = 0.5


def main() -> int:
    if not PROCESSED_PATH.exists():
        logger.error("%s does not exist — nothing to correct", PROCESSED_PATH)
        return 0

    problems = json.loads(PROCESSED_PATH.read_text(encoding="utf-8"))
    if not problems:
        logger.info("no problems in %s — nothing to correct", PROCESSED_PATH)
        return 0

    dated = [p for p in problems if p.get("first_seen_at")]
    if not dated:
        logger.info("no problem has first_seen_at set yet — nothing to correct")
        return 0

    backfill_date, backfill_count = Counter(p["first_seen_at"] for p in dated).most_common(1)[0]

    try:
        backfill_date_obj = datetime.fromisoformat(backfill_date).date()
    except ValueError:
        logger.warning("most common first_seen_at %r isn't a valid ISO date — leaving everything alone", backfill_date)
        return 0

    today = datetime.now(timezone.utc).date()
    days_old = (today - backfill_date_obj).days

    if days_old > NEW_BADGE_DAYS:
        logger.info(
            "most common first_seen_at (%s, %d problem(s)) is already %d days old "
            "(> NEW_BADGE_DAYS=%d) — nothing currently reads as falsely \"New\" from it; "
            "nothing to correct (this is what makes a second run a no-op)",
            backfill_date, backfill_count, days_old, NEW_BADGE_DAYS,
        )
        return 0

    majority_fraction = backfill_count / len(problems)
    if majority_fraction < MIN_MAJORITY_FRACTION:
        logger.info(
            "most common first_seen_at (%s) only accounts for %d/%d problem(s) (%.0f%%, "
            "below the %.0f%% bulk-stamp threshold) — doesn't look like a backfill artifact, "
            "leaving everything alone",
            backfill_date, backfill_count, len(problems), majority_fraction * 100, MIN_MAJORITY_FRACTION * 100,
        )
        return 0

    corrected_date = (today - timedelta(days=CORRECTED_AGE_DAYS)).isoformat()
    touched = 0
    for problem in problems:
        if problem.get("first_seen_at") == backfill_date:
            problem["first_seen_at"] = corrected_date
            touched += 1

    PROCESSED_PATH.write_text(json.dumps(problems, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "re-dated %d problem(s) from %s -> %s (were falsely reading as \"New\"; "
        "%d problem(s) with a different first_seen_at were left untouched)",
        touched, backfill_date, corrected_date, len(problems) - touched,
    )
    return touched


if __name__ == "__main__":
    main()
