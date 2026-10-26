"""
Real scraper for AngelHack's currently-featured events (its homepage's
"Latest Events" section) — part of the separate "Live Hackathons" feed,
not the problem-statement corpus pipeline.

angelhack.com is server-rendered WordPress + Elementor, so plain
requests + BeautifulSoup is enough. robots.txt only disallows /wp-admin/,
so the homepage is fair game for generic crawlers.

Verified against the live page (see docstring note below) that event
cards are the only `h2.elementor-heading-title` elements on the page
wrapped in an `<a href="…/event/…">` — every other heading on the page
(section titles like "Latest Events" itself, "News & Insights", blog post
titles, etc.) has no such wrapping link. That's a more robust signal than
assuming a fixed DOM nesting depth under the "Latest Events" heading,
since Elementor's own wrapper `<div>` nesting has no stable/semantic
class names to anchor a selector to.
"""

from __future__ import annotations

import logging
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


class LiveAngelHackScraper(BaseScraper):
    """AngelHack's currently-featured hackathons/events."""

    source_name = "angelhack"

    def __init__(self, timeout: int = 20):
        self.base_url = "https://angelhack.com/"
        self.timeout = timeout

    def fetch(self) -> list[dict]:
        response = requests.get(self.base_url, headers=_HEADERS, timeout=self.timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        return self.parse(soup)

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        """Parsing logic split out from fetch() so it can be unit-tested
        against a saved/fixture HTML page without hitting the network."""
        fetched_at = datetime.now(timezone.utc).isoformat()
        records: list[dict] = []
        seen_urls: set[str] = set()

        for heading in soup.find_all("h2", class_="elementor-heading-title"):
            link = heading.find_parent("a", href=True)
            if link is None or "/event/" not in link["href"]:
                continue
            title = heading.get_text(strip=True)
            url = link["href"].strip()
            if not title or not url or url in seen_urls:
                continue
            seen_urls.add(url)
            records.append({"title": title, "source": self.source_name, "url": url, "fetched_at": fetched_at})

        if not records:
            logger.warning("AngelHack page structure changed — found no event cards")
        logger.info("Live AngelHack scraper parsed %d event(s) from %s", len(records), self.base_url)
        return records
