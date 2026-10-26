"""
Unstop, DoraHacks and Kaggle are genuinely blocked by active anti-bot
protection (see each scraper's own docstring for what was verified
live) — these scrapers deliberately stay unimplemented rather than
attempting to work around that. This just locks in that they behave
like any other scraper in this state: fetch() returns an empty list
(honest "nothing scraped", never fabricated data) and run_safe() stays
graceful even if something inside were to raise.
"""

from app.scrapers.live_dorahacks_scraper import LiveDoraHacksScraper
from app.scrapers.live_kaggle_scraper import LiveKaggleScraper
from app.scrapers.live_unstop_scraper import LiveUnstopScraper


def test_unstop_fetch_returns_empty_list():
    assert LiveUnstopScraper().fetch() == []
    assert LiveUnstopScraper().run_safe() == []


def test_dorahacks_fetch_returns_empty_list():
    assert LiveDoraHacksScraper().fetch() == []
    assert LiveDoraHacksScraper().run_safe() == []


def test_kaggle_fetch_returns_empty_list():
    assert LiveKaggleScraper().fetch() == []
    assert LiveKaggleScraper().run_safe() == []


def test_source_names_are_set():
    assert LiveUnstopScraper.source_name == "unstop"
    assert LiveDoraHacksScraper.source_name == "dorahacks"
    assert LiveKaggleScraper.source_name == "kaggle"
