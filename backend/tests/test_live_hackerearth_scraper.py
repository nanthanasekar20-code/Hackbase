"""
Unit test for LiveHackerEarthScraper's HTML parsing logic, using a
fixture shaped like HackerEarth's real rendered listing (verified live):
each card is an `<a aria-label="View <title>" href=".../challenges/
hackathon/<slug>/">` with no visible text content of its own. Doesn't
hit the network.
"""

from bs4 import BeautifulSoup

from app.scrapers.live_hackerearth_scraper import LiveHackerEarthScraper

FIXTURE_HTML = """
<html><body>
<a class="absolute inset-0 z-0 rounded-xl" aria-label="View HackCellence: The Embark Edition"
   href="https://www.hackerearth.com/challenges/hackathon/hackcellence-the-embark-edition/"></a>
<a aria-label="View VibeCode Arena: AI Innovation Arena"
   href="https://www.hackerearth.com/challenges/hackathon/vibecode-arena-ai-innovation-arena/"></a>
<a aria-label="Not a hackathon card" href="https://www.hackerearth.com/practice/"></a>
<a href="https://www.hackerearth.com/challenges/hackathon/no-aria-label/">No aria-label, skip</a>
</body></html>
"""


def test_parses_title_from_aria_label_stripping_view_prefix():
    soup = BeautifulSoup(FIXTURE_HTML, "html.parser")
    records = LiveHackerEarthScraper().parse(soup)
    titles = {r["title"] for r in records}
    assert titles == {"HackCellence: The Embark Edition", "VibeCode Arena: AI Innovation Arena"}
    assert all(r["source"] == "hackerearth" for r in records)


def test_non_hackathon_links_are_excluded():
    soup = BeautifulSoup(FIXTURE_HTML, "html.parser")
    records = LiveHackerEarthScraper().parse(soup)
    assert all("/challenges/hackathon/" in r["url"] for r in records)


def test_card_without_aria_label_is_skipped():
    soup = BeautifulSoup(FIXTURE_HTML, "html.parser")
    records = LiveHackerEarthScraper().parse(soup)
    assert all("no-aria-label" not in r["url"] for r in records)


def test_no_matching_cards_returns_empty_list():
    soup = BeautifulSoup("<html><body>nothing</body></html>", "html.parser")
    assert LiveHackerEarthScraper().parse(soup) == []
