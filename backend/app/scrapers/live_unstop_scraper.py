"""
Unstop blocks automated access to its hackathon listing specifically —
part of the separate "Live Hackathons" feed, not the problem-statement
corpus pipeline. (The existing app/scrapers/unstop_scraper.py is a
different, still-unimplemented scraper for the problem-statement corpus
— unrelated to this one, left untouched.)

Verified live, twice: a plain `requests.get()` to its public
`/api/public/opportunity/search-result` endpoint (robots.txt explicitly
`Allow: /api/public/*`, suggesting it's meant to be used) got the TLS
connection reset mid-handshake, and loading `unstop.com/hackathons` in a
real headless Chromium tab (via Playwright) failed the same way —
`net::ERR_CONNECTION_RESET`. unstop.com/ (the homepage) loads fine
through the same browser, so this is targeted at the listing/API paths
specifically, not a general network issue — i.e. active bot protection,
not a parsing problem to work around. Retrying with different headers,
proxies, or stealth techniques would cross from "access like a normal
browser" into deliberately evading that protection, so this stays
unimplemented rather than attempting that.
"""

from __future__ import annotations

from app.scrapers.base_scraper import BaseScraper


class LiveUnstopScraper(BaseScraper):
    source_name = "unstop"

    def fetch(self) -> list[dict]:
        return []
