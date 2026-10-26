"""
Real scraper for currently-open hackathons on Devfolio — part of the
separate "Live Hackathons" feed, not the problem-statement corpus
pipeline.

devfolio.co/hackathons/open renders its listing entirely client-side —
confirmed live: the page's own `__NEXT_DATA__` payload (Next.js's usual
SSR data embed) carries only `{"filterType": ...}`, none of the actual
hackathon data, meaning it's fetched and rendered after hydration, not
server-rendered. devfolio.co/robots.txt allows generic crawling
(`User-agent: * / Disallow:`), so this uses a real headless browser
(see app/scrapers/playwright_utils.py) rather than trying to reverse-
engineer an undocumented internal API.

Each open hackathon gets its own `<subdomain>.devfolio.co` link on the
listing page; a fixed set of known non-hackathon subdomains (docs,
status, etc.) is excluded.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.scrapers.base_scraper import BaseScraper
from app.scrapers.playwright_utils import render_html

logger = logging.getLogger(__name__)

# Real subdomains on devfolio.co that are never a hackathon's own page —
# verified live (these appeared in the same link list as real hackathons
# on the /hackathons/open listing).
_NON_HACKATHON_SUBDOMAINS = {"www", "guide", "status", "blog", "help", "learn", "docs", "api"}


class LiveDevfolioScraper(BaseScraper):
    """Currently-open hackathons listed on Devfolio."""

    source_name = "devfolio"

    def __init__(self):
        self.base_url = "https://devfolio.co/hackathons/open"

    def fetch(self) -> list[dict]:
        html = render_html(self.base_url, wait_ms=4000)
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
            parsed = urlparse(href)
            if not parsed.netloc.endswith(".devfolio.co"):
                continue
            subdomain = parsed.netloc.removesuffix(".devfolio.co")
            if subdomain in _NON_HACKATHON_SUBDOMAINS:
                continue

            title = link.get_text(strip=True)
            if not title or href in seen_urls:
                continue
            seen_urls.add(href)
            records.append({"title": title, "source": self.source_name, "url": href, "fetched_at": fetched_at})

        if not records:
            logger.warning("Devfolio page structure changed — found no hackathon cards")
        logger.info("Live Devfolio scraper parsed %d hackathon(s) from %s", len(records), self.base_url)
        return records
