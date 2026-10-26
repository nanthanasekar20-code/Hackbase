"""
Real scraper for upcoming Major League Hacking (MLH) season events —
part of the separate "Live Hackathons" feed, not the problem-statement
corpus pipeline.

mlh.io permanently redirects to www.mlh.com (a real HTTP 302, verified
live) — this scraper targets www.mlh.com directly. That page is server-
rendered via Inertia.js, which embeds the full page payload (including
the events listing) as a <script data-page="app" type="application/json">
tag in the initial HTML response — no client-side JS execution needed to
read it, so plain requests + a small regex/json pull is enough.
www.mlh.com/robots.txt allows the /seasons/ path for generic crawlers.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

import requests

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}

_PAYLOAD_RE = re.compile(r'<script data-page="app" type="application/json">(.*?)</script>', re.S)


class LiveMLHScraper(BaseScraper):
    """Upcoming Major League Hacking season events."""

    source_name = "mlh"

    def __init__(self, season_year: str = "2026", timeout: int = 20):
        self.base_url = f"https://www.mlh.com/seasons/{season_year}/events"
        self.timeout = timeout

    def fetch(self) -> list[dict]:
        response = requests.get(self.base_url, headers=_HEADERS, timeout=self.timeout)
        response.raise_for_status()
        return self.parse(response.text)

    def parse(self, html: str) -> list[dict]:
        """Parsing logic split out from fetch() so it can be unit-tested
        against a saved/fixture HTML page without hitting the network."""
        match = _PAYLOAD_RE.search(html)
        if not match:
            logger.warning("MLH page structure changed — could not find the embedded events JSON payload")
            return []
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            logger.warning("MLH embedded events payload was not valid JSON")
            return []

        events = (payload.get("props") or {}).get("upcomingEvents") or []
        fetched_at = datetime.now(timezone.utc).isoformat()
        records: list[dict] = []

        for event in events:
            title = (event.get("name") or "").strip()
            relative_url = event.get("url")
            url = event.get("websiteUrl") or (f"https://www.mlh.com{relative_url}" if relative_url else None)
            if not title or not url:
                continue
            records.append(
                {
                    "title": title,
                    "source": self.source_name,
                    "url": url,
                    "deadline": event.get("dateRange") or None,
                    "fetched_at": fetched_at,
                }
            )

        logger.info("Live MLH scraper parsed %d upcoming event(s) from %s", len(records), self.base_url)
        return records
