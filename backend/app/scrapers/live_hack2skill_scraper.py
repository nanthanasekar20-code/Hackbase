"""
Real scraper for hackathons featured on Hack2Skill's homepage — part of
the separate "Live Hackathons" feed, not the problem-statement corpus
pipeline.

hack2skill.com renders its event list client-side (a Vite/React app —
the raw HTTP response's listing area is just unfilled `${item.title}`-
style template placeholders, confirmed live), so this uses a real
headless browser (see app/scrapers/playwright_utils.py). robots.txt
explicitly `Allow: /event/` alongside the general `Allow: /`.

Only cards whose own status text indicates registration is actually open
are kept — most cards on the homepage are past ("Registration closed")
events, and the user asked for hackathons *currently open for
registration*, not a full history. Each card's `<a href=".../event/...">`
wraps a container that also holds the status text and a heading with the
real event title (verified live — the link's own innerText is just the
button label, e.g. "Register Now", not the title).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from app.scrapers.base_scraper import BaseScraper
from app.scrapers.playwright_utils import render_html

logger = logging.getLogger(__name__)

# Real status strings seen on live cards — anything else (e.g.
# "Registration closed") is a past event, not currently open.
_OPEN_STATUSES = {"register now", "registration open", "registrations open"}


class LiveHack2SkillScraper(BaseScraper):
    """Hack2Skill events whose registration is currently open."""

    source_name = "hack2skill"

    def __init__(self):
        self.base_url = "https://hack2skill.com/"

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
            if "/event/" not in href:
                continue
            status = link.get_text(strip=True).lower()
            if status not in _OPEN_STATUSES:
                continue

            card = link
            for _ in range(4):
                if card.parent is None:
                    break
                card = card.parent
            heading = card.find(["h1", "h2", "h3", "h4", "h5"])
            title = heading.get_text(strip=True) if heading else ""
            if not title or href in seen_urls:
                continue
            seen_urls.add(href)
            records.append({"title": title, "source": self.source_name, "url": href, "fetched_at": fetched_at})

        logger.info(
            "Live Hack2Skill scraper parsed %d open-for-registration hackathon(s) from %s",
            len(records),
            self.base_url,
        )
        return records
