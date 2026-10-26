"""
One-time backfill for scripts/enrich_resume_value.py's incomplete-score
side effect — NOT a change to how enrichment normally runs, just a single
migration pass over data/processed/problems.json.

Why this exists: enrich_resume_value.py now scores nine fields per
problem in one Gemini call (SCORE_FIELDS), but it originally only scored
three (resume_value_score, industry_relevance_score,
technical_depth_score). Every problem enriched before the other six
fields existed already has resume_value_score set, and the old gating
check ("resume_value_score is None") — used by both enrich()'s batch pass
and the lazy per-save trigger in app/api/routes/favorites.py — treated
"has resume_value_score" as "fully done" forever, so those problems would
never pick up the six missing fields on their own, even on a fresh save.

That gating check is now is_fully_scored() (checks all nine fields, not
just one) — see enrich_resume_value.py. This script doesn't duplicate any
prompt/parsing/write-back logic: it just calls enrich_resume_value.enrich(),
which now correctly treats "missing any of the nine fields" as needing
enrichment, and reuses enrich()'s existing batching/retry/checkpointing.
This script exists only to document why that one-time pass is needed and
to report a clear before/after summary for it.

Run as: python scripts/backfill_missing_score_fields.py [--batch-size N]

Idempotent: once every problem has all nine fields, enrich() finds
nothing left needing enrichment and this is a no-op. Safe to re-run if an
earlier run stopped partway (e.g. Gemini daily quota exhausted) — it
picks up exactly where it left off, same checkpointing enrich() already
does for its regular batch pass.
"""

from __future__ import annotations

import argparse
import json
import logging

from scripts.enrich_resume_value import DEFAULT_BATCH_SIZE, PROCESSED_PATH, SCORE_FIELDS, enrich, is_fully_scored

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main(batch_size: int = DEFAULT_BATCH_SIZE) -> int:
    if not PROCESSED_PATH.exists():
        logger.error("%s does not exist — nothing to backfill", PROCESSED_PATH)
        return 0

    problems = json.loads(PROCESSED_PATH.read_text(encoding="utf-8"))
    total = len(problems)
    already_full = sum(1 for p in problems if is_fully_scored(p))
    missing = total - already_full

    logger.info(
        "%d/%d problem(s) already have all %d score fields; %d missing at least one field",
        already_full, total, len(SCORE_FIELDS), missing,
    )
    if missing == 0:
        logger.info("nothing to backfill")
        return 0

    backfilled = enrich(force=False, batch_size=batch_size)

    logger.info(
        "backfill complete: %d problem(s) newly/fully scored this run, %d already had all %d fields and were skipped",
        backfilled, already_full, len(SCORE_FIELDS),
    )
    return backfilled


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()
    main(batch_size=args.batch_size)
