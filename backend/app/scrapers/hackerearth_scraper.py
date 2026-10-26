"""
HackerEarth has no scrapable problem-statement content — part of the main
problem corpus (data/processed/problems.json via scripts/run_scrapers.py
-> build_corpus.py). Separate from app/scrapers/live_hackerearth_scraper.py
(the Live Hackathons feed's scraper), which only needs each hackathon's
name + link and works fine via Playwright. This one needs real problem/
project-prompt text, and that genuinely isn't available here — a
different kind of limitation than Unstop's (not bot-blocking; verified
live below).

hackerearth.com/challenges/hackathon/ itself is just a bare listing —
rendered via Playwright and inspected card-by-card, each card has only a
title, organizer name, participant count and a "Join Now" button; no
description text anywhere in the card markup.

Following a real listing link doesn't lead to HackerEarth-hosted content
at all: every hackathon checked (3/3, the same ones
live_hackerearth_scraper.py found) redirects off-site to a completely
different, unrelated domain the *organizer* built independently —
booking.hackerearth.com (itself an iframe wrapping a custom React app
built with the "Lovable" site builder), vibecodearena.ai, and
yuvayodhatech.com. There is no common page structure across these to
scrape at all — HackerEarth is purely a discovery/listing layer, and the
real content lives on an arbitrary external site per hackathon, each
needing its own bespoke scraper (and even a universal fallback like a
`<meta name="description">` tag isn't reliable: present with real text on
one of the three, empty on another).

Scraping just the listing-page title alone (with no real description)
wouldn't be a meaningful "problem statement" — it'd add sparse, near-empty
records to the corpus rather than real content, which is worse than not
scraping this source at all. Stays unimplemented, honestly, rather than
padding the corpus with titles-only placeholder-shaped records.
"""

from __future__ import annotations

from app.scrapers.base_scraper import BaseScraper


class HackerEarthScraper(BaseScraper):
    source_name = "hackerearth"

    def fetch(self) -> list[dict]:
        return []
