"""
Real scraper for hackathons listed on HackerEarth — part of the separate
"Live Hackathons" feed, not the problem-statement corpus pipeline. (The
existing app/scrapers/hackerearth_scraper.py is a different, still-
unimplemented scraper for the problem-statement corpus — unrelated to
this one, left untouched.)

hackerearth.com/challenges/hackathon/ renders its listing client-side
(the raw HTTP response has no card markup), so this uses a real headless
browser (see app/scrapers/playwright_utils.py). robots.txt allows the
default crawl (`User-agent: * / Allow: /`), only disallowing login/AJAX/
locale-prefixed paths.

Each card is an `<a aria-label="View <title>" href=".../challenges/
hackathon/<slug>/">` with no visible text content of its own (the title
is rendered as a background/overlay image) — verified live that the
clean title is the aria-label with its "View " prefix stripped.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from app.scrapers.base_scraper import BaseScraper
from app.scrapers.playwright_utils import render_html

logger = logging.getLogger(__name__)


class LiveHackerEarthScraper(BaseScraper):
    """Hackathons listed on HackerEarth."""

    source_name = "hackerearth"

    def __init__(self):
        self.base_url = "https://www.hackerearth.com/challenges/hackathon/"

    def fetch(self) -> list[dict]:
        # A couple of scroll ticks — some cards lazy-load just below the fold.
        html = render_html(self.base_url, wait_ms=3000, scroll_times=3)
        soup = BeautifulSoup(html, "html.parser")
        return self.parse(soup)

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        """Parsing logic split out from fetch() so it can be unit-tested
        against saved/fixture rendered HTML without a real browser."""
        fetched_at = datetime.now(timezone.utc).isoformat()
        records: list[dict] = []
        seen_urls: set[str] = set()

        for link in soup.find_all("a", href=True, attrs={"aria-label": True}):
            href = link["href"]
            if "/challenges/hackathon/" not in href:
                continue
            label = link["aria-label"].strip()
            title = label[len("View ") :].strip() if label.lower().startswith("view ") else label
            if not title or href in seen_urls:
                continue
            seen_urls.add(href)
            records.append({"title": title, "source": self.source_name, "url": href, "fetched_at": fetched_at})

        if not records:
            logger.warning("HackerEarth page structure changed — found no hackathon cards")
        logger.info("Live HackerEarth scraper parsed %d hackathon(s) from %s", len(records), self.base_url)
        return records
