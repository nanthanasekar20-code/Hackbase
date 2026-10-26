"""
DoraHacks sits behind active bot protection — part of the separate
"Live Hackathons" feed, not the problem-statement corpus pipeline.

Verified live: every request to dorahacks.io (including its own
robots.txt) returns an AWS WAF "Human Verification" interstitial — a
JS-rendered CAPTCHA challenge page, not the real site content, with no
server-rendered fallback to read instead. There's no way to get real
listing data here without solving that CAPTCHA programmatically, which
is deliberately evading anti-bot protection rather than scraping like a
normal visitor — so this stays unimplemented rather than attempting that.
"""

from __future__ import annotations

from app.scrapers.base_scraper import BaseScraper


class LiveDoraHacksScraper(BaseScraper):
    source_name = "dorahacks"

    def fetch(self) -> list[dict]:
        return []
