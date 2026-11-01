"""
Real scraper for NASA Space Apps Challenge problem statements — part of
the main problem corpus (data/processed/problems.json via
scripts/run_scrapers.py -> build_corpus.py).

Page structure: https://www.spaceappschallenge.org/{year}/challenges/
lists every challenge as an `<a href="/{year}/challenges/<slug>/">` link
(confirmed live: 18 real challenges in the 2025 listing). Each
challenge's own page (rendered the same way) carries a real, detailed,
per-challenge problem statement under four headings — Summary,
Background, Objectives, Potential Considerations — not a generic
site-wide blurb, which is why Devpost stays unregistered here (see
scripts/run_scrapers.py).

Both the listing and detail pages are Next.js, fully client-rendered
(confirmed live: no real content in the raw HTML's __NEXT_DATA__), so
this uses a real headless browser (see app/scrapers/playwright_utils.py),
same as live_devfolio_scraper.py / live_hackerearth_scraper.py.

Note: spaceappschallenge.org's main domain currently serves an
incomplete TLS certificate chain — a plain `requests` call fails cert
verification (missing intermediate), while a real browser (this
scraper's Playwright rendering, same as any real visitor) resolves it
fine via its own trust store. That's exactly why this uses the same
real-browser approach as the other JS-rendered sources already do,
rather than ever disabling certificate verification.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.core.config import settings
from app.scrapers.base_scraper import BaseScraper
from app.scrapers.playwright_utils import render_html

logger = logging.getLogger(__name__)

_SECTION_HEADINGS = ("Summary", "Background", "Objectives", "Potential Considerations")


def _section_text(heading) -> str:
    """Collects the text between one <h2> section heading and the next."""
    parts = []
    for sib in heading.find_next_siblings():
        if sib.name == "h2":
            break
        text = sib.get_text(" ", strip=True)
        if text:
            parts.append(text)
    return " ".join(parts)


class NasaSpaceAppsScraper(BaseScraper):
    """NASA Space Apps Challenge's own per-challenge problem statements."""

    source_name = "nasa_spaceapps"

    def __init__(self, year: str | None = None):
        self.year = year or getattr(settings, "nasa_spaceapps_year", "2025")
        self.base_url = f"https://www.spaceappschallenge.org/{self.year}/challenges/"

    def fetch(self) -> list[dict]:
        listing_soup = BeautifulSoup(render_html(self.base_url, wait_ms=5000, scroll_times=3), "html.parser")
        urls = self._extract_challenge_urls(listing_soup)

        records: list[dict] = []
        for url in urls:
            detail_soup = BeautifulSoup(render_html(url, wait_ms=5000), "html.parser")
            record = self.parse(detail_soup, url)
            if record:
                records.append(record)

        logger.info("NASA Space Apps scraper parsed %d challenge(s) from %s", len(records), self.base_url)
        return records

    def _extract_challenge_urls(self, soup: BeautifulSoup) -> list[str]:
        """Split out from fetch() so it's unit-testable against a saved listing page."""
        marker = f"/{self.year}/challenges/"
        urls: list[str] = []
        seen = set()
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if marker not in href or href.rstrip("/").endswith("challenges"):
                continue  # the "challenges" index link itself, not a real challenge
            full_url = urljoin(self.base_url, href)
            if full_url in seen:
                continue
            seen.add(full_url)
            urls.append(full_url)
        return urls

    def parse(self, soup: BeautifulSoup, url: str) -> dict | None:
        """Mapping logic split out from fetch() so it can be unit-tested
        against saved/fixture rendered HTML without a real browser."""
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title:
            logger.warning("NASA Space Apps page at %s has no <h1> title — skipping", url)
            return None

        sections = {
            h2.get_text(strip=True): _section_text(h2)
            for h2 in soup.find_all("h2")
            if h2.get_text(strip=True) in _SECTION_HEADINGS
        }
        description = "\n\n".join(f"{label}: {sections[label]}" for label in _SECTION_HEADINGS if sections.get(label))
        if not description:
            # A challenge page with a title but none of its real section
            # text wouldn't be a meaningful problem statement — same
            # judgment call as HackerEarth's titles-only case (see
            # hackerearth_scraper.py): skip rather than pad the corpus.
            logger.warning("NASA Space Apps challenge %r has no section text — skipping", title)
            return None

        slug = url.rstrip("/").rsplit("/", 1)[-1]
        return {
            "title": title,
            "description": description,
            "organization": "NASA",
            "source": self.source_name,
            "hackathon_name": f"NASA Space Apps Challenge {self.year}",
            "external_id": f"nasa_spaceapps:{slug}" if slug else None,
            "category": None,
            "theme": self._subjects_text(soup) or None,
            "url": url,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    def _subjects_text(self, soup: BeautifulSoup) -> str:
        for h3 in soup.find_all("h3"):
            if h3.get_text(strip=True) == "Subjects":
                sib = h3.find_next_sibling()
                if sib:
                    return ", ".join(sib.stripped_strings)
        return ""
