"""
Runs scripts/run_live_hackathons.py on a timer — a separate, unrelated
job from app/services/refresh_job.py (the problem-statement corpus
refresh). Wired up as its own APScheduler job in app/main.py so the two
feeds refresh independently and a change to one's schedule/behavior
never touches the other.

Called by:
  - the APScheduler job wired up in app/main.py (automatic, every
    settings.live_hackathons_refresh_interval_hours)
  - directly, for a manual one-off refresh (e.g. from a Python shell)

Safe to call from a background thread: scripts.run_live_hackathons.run()
already runs every scraper through run_safe() (one failing/blocked site
can't take down the others), and this wraps the whole call too so a
failure here can't crash the scheduler thread or the app process.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def run_live_hackathons_refresh() -> dict:
    """Runs one live-hackathons scrape -> merge -> write cycle. Returns
    the written payload (or an error summary); never raises."""
    try:
        from scripts.run_live_hackathons import run as run_live_hackathons

        payload = run_live_hackathons()

        # app/core/live_hackathons.py caches the file's contents in memory
        # per process — without this, GET /live-hackathons would keep
        # serving the pre-refresh feed until the app restarts.
        from app.core.live_hackathons import reset_cache

        reset_cache()

        logger.info("live_hackathons_job: completed successfully (%d hackathons)", payload["count"])
        return payload
    except Exception:
        logger.exception("live_hackathons_job: failed")
        return {"ok": False}
