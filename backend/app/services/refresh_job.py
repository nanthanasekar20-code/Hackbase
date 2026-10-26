"""
Orchestrates the full "get new hackathon problems in front of users"
pipeline as one function, so it can run on a timer instead of someone
running three scripts by hand:

    scripts/run_scrapers.py   -> data/raw/*.json
    scripts/build_corpus.py   -> data/processed/problems.json (clean/dedup/
                                  tag, preserves existing resume-value
                                  scores and first_seen_at by id, stamps
                                  first_seen_at on genuinely new ids)
    app/rag/index_builder.py  -> rebuilds the Chroma index from the new
                                  problems.json

Deliberately does NOT run scripts/enrich_resume_value.py here — that's a
per-problem Gemini call, and scoring every newly-scraped problem on every
scheduled refresh would spend API quota on problems nobody has looked at
yet. Instead, app/api/routes/favorites.py enriches a problem lazily, the
first time a signed-in user actually saves it (see enrich_one() in
scripts/enrich_resume_value.py) — enrichment cost then scales with real
interest, not with how many new problems a scrape happened to find.

Called by:
  - the APScheduler job wired up in app/main.py (automatic, every
    settings.auto_refresh_interval_hours)
  - directly, for a manual one-off refresh (e.g. from a Python shell)

Safe to call from a background thread: each stage is wrapped so one
failing stage (a scraper site down, a bad write) is logged and stops
this run without crashing the app process or the scheduler itself —
run_safe() on each individual scraper already handles a single source
failing without stopping the others; this is the same philosophy one
level up.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def run_refresh() -> dict:
    """Runs one full scrape -> rebuild -> reindex cycle. Returns a small
    summary dict; never raises — failures are logged and reflected in the
    returned dict's `error` field instead, so a bad run doesn't take down
    the scheduler thread or the app."""
    summary = {"ok": False, "stage": None, "problems_indexed": None, "error": None}

    try:
        summary["stage"] = "scrape"
        from scripts.run_scrapers import main as run_scrapers

        run_scrapers()

        summary["stage"] = "build_corpus"
        from scripts.build_corpus import main as build_corpus

        build_corpus()

        summary["stage"] = "index"
        from app.rag.index_builder import build_index

        count = build_index()
        summary["problems_indexed"] = count

        # app/core/corpus.py caches problems.json in memory per process —
        # without this, favorites/roadmap pages would keep serving the
        # pre-refresh corpus until the app restarts.
        summary["stage"] = "reset_cache"
        from app.core.corpus import reset_cache

        reset_cache()

        summary["ok"] = True
        summary["stage"] = None
        logger.info("refresh_job: completed successfully (%d problems indexed)", count)
    except Exception as exc:  # noqa: BLE001 - deliberately broad, see docstring
        logger.exception("refresh_job: failed at stage %r", summary["stage"])
        summary["error"] = str(exc)

    return summary
