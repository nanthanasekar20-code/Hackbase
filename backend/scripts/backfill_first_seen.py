"""
One-time migration: stamps first_seen_at on every problem in
data/processed/problems.json that doesn't already have one, using
TODAY's date as a neutral baseline.

WITHOUT running this once, the next build_corpus.py run (manual or via
the new scheduled refresh_job) would treat every one of the current
problems as newly-discovered — since none of them have a first_seen_at
yet — and the frontend's "New" badge would light up on the entire
existing corpus instead of only on problems actually added going
forward.

Run this ONCE, right after pulling in the first_seen_at change and
before enabling the scheduler (AUTO_REFRESH_ENABLED) or running
build_corpus.py again:

    python scripts/backfill_first_seen.py

Safe to run more than once — it only touches problems that still have no
first_seen_at, so a second run is a no-op.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_PATH = ROOT / "data" / "processed" / "problems.json"


def main() -> int:
    if not PROCESSED_PATH.exists():
        logger.error("%s does not exist — nothing to backfill", PROCESSED_PATH)
        return 0

    problems = json.loads(PROCESSED_PATH.read_text(encoding="utf-8"))
    today = datetime.now(timezone.utc).date().isoformat()

    stamped = 0
    for problem in problems:
        if not problem.get("first_seen_at"):
            problem["first_seen_at"] = today
            stamped += 1

    if stamped:
        PROCESSED_PATH.write_text(
            json.dumps(problems, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    logger.info(
        "stamped first_seen_at=%s on %d/%d problem(s) (already had one: %d)",
        today,
        stamped,
        len(problems),
        len(problems) - stamped,
    )
    return stamped


if __name__ == "__main__":
    main()
