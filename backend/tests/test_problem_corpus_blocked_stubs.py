"""
Unstop and HackerEarth are genuinely unscrapable for the main problem
corpus — Unstop by intermittent active bot-blocking, HackerEarth because
its real content lives on arbitrary external sites with no common
structure (see each scraper's own docstring for what was verified live).
Both stay unimplemented rather than faking data; this just locks in that
they behave like any other scraper in that state.
"""

from app.scrapers.hackerearth_scraper import HackerEarthScraper
from app.scrapers.unstop_scraper import UnstopScraper


def test_unstop_fetch_returns_empty_list():
    assert UnstopScraper().fetch() == []
    assert UnstopScraper().run_safe() == []


def test_hackerearth_fetch_returns_empty_list():
    assert HackerEarthScraper().fetch() == []
    assert HackerEarthScraper().run_safe() == []


def test_source_names_are_set():
    assert UnstopScraper.source_name == "unstop"
    assert HackerEarthScraper.source_name == "hackerearth"
