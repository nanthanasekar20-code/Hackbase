"""
Real scraper for currently-active Kaggle competitions, via Kaggle's
official public API (the `kaggle` PyPI package) — part of the separate
"Live Hackathons" feed (see scripts/run_live_hackathons.py), not the
problem-statement corpus pipeline.

Kaggle's own site sits behind Google reCAPTCHA Enterprise for
anonymous/automated requests — verified live: even a plain GET to
kaggle.com/robots.txt returns a "Checking your browser" interstitial,
not real content. That isn't a page-structure problem to work around
with a different parser or a headless browser (reCAPTCHA Enterprise is
specifically designed to resist that). Kaggle's official API is the
sanctioned way to read this data instead — but it requires a real
user's own API credentials (KAGGLE_USERNAME / KAGGLE_KEY, from
https://www.kaggle.com/settings -> API -> Create New Token), which this
scraper can't supply on its own.

Same honest-degradation philosophy as every other scraper here: with no
credentials configured (the default — see .env.example), fetch() logs
why and returns [] rather than ever fabricating output or raising. This
mirrors how SMTP_HOST="" leaves password-reset email unconfigured
elsewhere in this app (see app/core/config.py) instead of pretending.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from app.core.config import settings
from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class LiveKaggleScraper(BaseScraper):
    """Currently-active competitions from Kaggle's official public API."""

    source_name = "kaggle"

    def fetch(self) -> list[dict]:
        if not settings.kaggle_username or not settings.kaggle_key:
            logger.info(
                "Kaggle scraper skipped: KAGGLE_USERNAME/KAGGLE_KEY aren't "
                "configured (see .env.example) — leaving this source empty "
                "rather than guessing at credentials."
            )
            return []

        # The `kaggle` package reads these env vars (or a
        # ~/.kaggle/kaggle.json file) at authenticate()-time, not import
        # time — setting them here keeps real credentials flowing through
        # the same .env -> app/core/config.py path every other credential
        # in this app uses, instead of a separate kaggle.json file.
        os.environ["KAGGLE_USERNAME"] = settings.kaggle_username
        os.environ["KAGGLE_KEY"] = settings.kaggle_key

        # Imported lazily so importing this module never requires Kaggle
        # credentials to exist — only calling fetch() with them configured
        # does.
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()
        # category left at its default (unspecified) deliberately — per
        # the kaggle package's own docstring, that's what excludes closed
        # competitions ("use 'all' to get closed competitions"), so this
        # is already "active only" without extra client-side filtering.
        response = api.competitions_list(group="general", sort_by="earliestDeadline", page_size=50)
        return self.parse(response.competitions if response else [])

    def parse(self, competitions: list) -> list[dict]:
        """Mapping logic split out from fetch() so it can be unit-tested
        against fixture competition objects without hitting the network."""
        fetched_at = datetime.now(timezone.utc).isoformat()
        records: list[dict] = []

        for comp in competitions:
            title = (getattr(comp, "title", "") or "").strip()
            url = (getattr(comp, "url", "") or "").strip()
            if not title or not url:
                continue
            deadline = getattr(comp, "deadline", None)
            records.append(
                {
                    "title": title,
                    "source": self.source_name,
                    "url": url,
                    "deadline": deadline.isoformat() if deadline else None,
                    "fetched_at": fetched_at,
                }
            )

        logger.info("Live Kaggle scraper parsed %d active competition(s)", len(records))
        return records
