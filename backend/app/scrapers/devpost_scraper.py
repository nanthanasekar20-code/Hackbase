"""
Real scraper for Devpost hackathons, feeding the main problem corpus
(data/processed/problems.json via scripts/run_scrapers.py ->
build_corpus.py). Separate from app/scrapers/live_devpost_scraper.py,
which feeds the much simpler Live Hackathons feed (name/source/link
only, no description) — this one needs real problem/project-prompt text
per RawProblem, so it does more work per hackathon.

devpost.com/robots.txt allows generic crawling (`User-agent: * /
Disallow:`), confirmed live. Two real, stable data sources, no HTML
scraping of the listing page itself:

1. Devpost's own public JSON API (devpost.com/api/hackathons) — the same
   endpoint devpost.com/hackathons calls client-side, paginated
   (`meta.total_count` / `meta.per_page`), for the hackathon list itself
   (title, org, themes, url, dates).
2. Each hackathon's own page embeds its real "About" text server-rendered
   in `#challenge-description` (verified live against several hackathons)
   — plain requests + BeautifulSoup, no JS execution needed. This is the
   organizer's own real build prompt, used as `description`. Devpost
   hackathons don't have a standardized set of distinct per-sponsor
   "problem statements" the way SIH does (some have sponsor "Challenges"
   sections, most don't, with no consistent structure) — one real record
   per hackathon, same granularity app/scrapers/live_devpost_scraper.py
   already uses for the live feed.

Scoped to currently-OPEN hackathons only (same as the live feed) — real,
bounded (dozens, not thousands), and naturally refreshes as different
hackathons open over time via the scheduled corpus rebuild
(app/services/refresh_job.py). One hackathon-detail-page fetch failing
(a real network hiccup, a page that doesn't follow the usual structure)
is skipped and logged rather than failing the whole run.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}

API_URL = "https://devpost.com/api/hackathons"
# A short, polite pause between per-hackathon detail-page fetches — this
# scraper makes one extra real HTTP request per hackathon beyond the
# listing API, so this keeps it from hammering devpost.com in a tight loop.
DETAIL_FETCH_DELAY_SECONDS = 0.3


class DevpostScraper(BaseScraper):
    """Currently-open Devpost hackathons, each hydrated with its own real 'About' text."""

    source_name = "devpost"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def fetch(self) -> list[dict]:
        listings = self._fetch_all_open_hackathons()
        return self.parse(listings)

    def _fetch_all_open_hackathons(self) -> list[dict]:
        """Paginates devpost.com/api/hackathons?status[]=open to its real end
        (meta.total_count), rather than only the first page."""
        listings: list[dict] = []
        page = 1
        while True:
            response = requests.get(
                API_URL,
                params={"status[]": "open", "order_by": "recently-added", "page": page},
                headers=_HEADERS,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            batch = payload.get("hackathons", [])
            listings.extend(batch)

            total_count = (payload.get("meta") or {}).get("total_count", len(listings))
            if not batch or len(listings) >= total_count:
                break
            page += 1
        return listings

    def _fetch_description(self, url: str) -> str:
        response = requests.get(url, headers=_HEADERS, timeout=self.timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        el = soup.select_one("#challenge-description")
        return el.get_text(" ", strip=True) if el else ""

    def parse(self, listings: list[dict]) -> list[dict]:
        """Parsing/hydration logic split out from fetch() so the listing-
        level shape can be unit-tested against a fixture without the
        network; the per-hackathon description fetch is still real I/O
        (there's no "structure" to fixture-test there beyond the selector,
        already covered by the try/except below)."""
        fetched_at = datetime.now(timezone.utc).isoformat()
        records: list[dict] = []

        for item in listings:
            title = (item.get("title") or "").strip()
            url = (item.get("url") or "").strip()
            if not title or not url:
                continue

            try:
                description = self._fetch_description(url)
            except Exception as exc:  # a single hackathon's page acting up shouldn't lose the rest
                logger.warning("Devpost: could not fetch description for %r (%s): %s", title, url, exc)
                description = ""
            finally:
                time.sleep(DETAIL_FETCH_DELAY_SECONDS)

            themes = [t.get("name") for t in (item.get("themes") or []) if t.get("name")]
            records.append(
                {
                    "title": title,
                    "description": description,
                    "organization": item.get("organization_name") or None,
                    "source": self.source_name,
                    "hackathon_name": title,
                    "external_id": str(item["id"]) if item.get("id") is not None else None,
                    "category": themes[0] if themes else None,
                    "theme": ", ".join(themes) if themes else None,
                    "url": url,
                    "fetched_at": fetched_at,
                }
            )

        logger.info("Devpost scraper parsed %d open hackathon(s)", len(records))
        return records
