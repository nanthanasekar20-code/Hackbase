"""
Real scraper for hackathons listed on Taikai — part of the separate
"Live Hackathons" feed, not the problem-statement corpus pipeline.

taikai.network/hackathons renders its listing client-side (its
`__NEXT_DATA__` payload carries only routing info, no hackathon data,
confirmed live) and the page also never reaches `networkidle` (it holds
an open connection, likely a websocket/polling), so this waits for
`domcontentloaded` plus a fixed settle time instead. robots.txt only
disallows `/auth`, so the public listing is fair game for generic
crawlers.

Each card is an `<a href=".../hackathons/...">`; the clean hackathon
title lives in its cover image's `alt` attribute (verified live — the
link's own innerText is a jumble of status/stat-count/title/description
with no reliable separator, but `img[alt]` is just the title).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from app.scrapers.base_scraper import BaseScraper
from app.scrapers.playwright_utils import render_html

logger = logging.getLogger(__name__)


class LiveTaikaiScraper(BaseScraper):
    """Hackathons listed on Taikai."""

    source_name = "taikai"

    def __init__(self):
        self.base_url = "https://taikai.network/hackathons"

    def fetch(self) -> list[dict]:
        html = render_html(self.base_url, wait_ms=5000)
        soup = BeautifulSoup(html, "html.parser")
        return self.parse(soup)

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        """Parsing logic split out from fetch() so it can be unit-tested
        against saved/fixture rendered HTML without a real browser."""
        fetched_at = datetime.now(timezone.utc).isoformat()
        records: list[dict] = []
        seen_urls: set[str] = set()

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/hackathons/" not in href:
                continue
            img = link.find("img", alt=True)
            title = img["alt"].strip() if img else ""
            if not title or href in seen_urls:
                continue
            url = href if href.startswith("http") else f"https://taikai.network{href}"
            seen_urls.add(href)
            records.append({"title": title, "source": self.source_name, "url": url, "fetched_at": fetched_at})

        if not records:
            logger.warning("Taikai page structure changed — found no hackathon cards")
        logger.info("Live Taikai scraper parsed %d hackathon(s) from %s", len(records), self.base_url)
        return records
