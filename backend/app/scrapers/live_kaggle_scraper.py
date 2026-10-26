"""
Kaggle sits behind active bot protection for anonymous/automated
requests — part of the separate "Live Hackathons" feed, not the
problem-statement corpus pipeline.

Verified live: even a plain GET to kaggle.com/robots.txt returns a
Google reCAPTCHA Enterprise "Checking your browser" interstitial, not
real content — this isn't a page-structure problem to work around with a
different parser or a headless browser (reCAPTCHA Enterprise is
specifically designed to resist that).

The correct way to read Kaggle competitions programmatically is its
official public API (the `kaggle` PyPI package / `kaggle competitions
list`), which Kaggle explicitly provides for exactly this — but it
requires a real user's own Kaggle account API credentials
(KAGGLE_USERNAME / KAGGLE_KEY), which aren't something this scraper can
supply on its own. This stays unimplemented (never silently faking
output) until those credentials are configured; wiring up the official
API at that point would be a small, separate, well-scoped follow-up.
"""

from __future__ import annotations

from app.scrapers.base_scraper import BaseScraper


class LiveKaggleScraper(BaseScraper):
    source_name = "kaggle"

    def fetch(self) -> list[dict]:
        return []
