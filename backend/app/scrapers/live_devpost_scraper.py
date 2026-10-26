"""
Real scraper for currently-open hackathons on Devpost — part of the
separate "Live Hackathons" feed (see scripts/run_live_hackathons.py),
not the existing problem-statement corpus pipeline. Uses Devpost's own
public JSON API (the same endpoint devpost.com/hackathons itself calls
client-side to render its listing) instead of scraping rendered HTML —
devpost.com/robots.txt allows generic crawling of the whole site
(`User-agent: * / Disallow:`), and a clean documented-shape JSON
endpoint is a more stable, lower-impact source than parsing markup that
can change at any time.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


class LiveDevpostScraper(BaseScraper):
    """Currently-open hackathons from Devpost's public hackathons API."""

    source_name = "devpost"

    def __init__(self, timeout: int = 20):
        self.api_url = "https://devpost.com/api/hackathons"
        self.timeout = timeout

    def fetch(self) -> list[dict]:
        response = requests.get(
            self.api_url,
            params={"status[]": "open", "order_by": "recently-added"},
            headers=_HEADERS,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return self.parse(response.json())

    def parse(self, payload: dict) -> list[dict]:
        """Parsing logic split out from fetch() so it can be unit-tested
        against a saved/fixture JSON payload without hitting the network."""
        fetched_at = datetime.now(timezone.utc).isoformat()
        records: list[dict] = []

        for item in payload.get("hackathons", []):
            title = (item.get("title") or "").strip()
            url = (item.get("url") or "").strip()
            if not title or not url:
                continue
            records.append(
                {
                    "title": title,
                    "source": self.source_name,
                    "url": url,
                    "deadline": item.get("submission_period_dates") or None,
                    "fetched_at": fetched_at,
                }
            )

        logger.info("Live Devpost scraper parsed %d open hackathon(s)", len(records))
        return records
