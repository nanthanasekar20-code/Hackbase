"""
Unit test for LiveDevfolioScraper's HTML parsing logic, using a fixture
shaped like Devfolio's real rendered listing (verified live): each open
hackathon is a link to its own `<slug>.devfolio.co` subdomain; a handful
of real non-hackathon subdomains (guide, status, docs, ...) appear in the
same page and must be excluded. Doesn't hit the network — this is given
already-rendered HTML, the same shape playwright_utils.render_html()
would hand to parse() in fetch().
"""

from bs4 import BeautifulSoup

from app.scrapers.live_devfolio_scraper import LiveDevfolioScraper

FIXTURE_HTML = """
<html><body>
<a href="https://hackverse-19.devfolio.co/">Hackverse.2026</a>
<a href="https://sudo-hacktober.devfolio.co/">sudo Hacktober</a>
<a href="https://guide.devfolio.co/">Documentation</a>
<a href="https://status.devfolio.co/">Status</a>
<a href="https://www.devfolio.co/about">About</a>
<a href="https://hackverse-19.devfolio.co/">Hackverse.2026</a>
</body></html>
"""


def test_parses_real_hackathon_subdomains_only():
    soup = BeautifulSoup(FIXTURE_HTML, "html.parser")
    records = LiveDevfolioScraper().parse(soup)
    titles = {r["title"] for r in records}
    assert titles == {"Hackverse.2026", "sudo Hacktober"}
    assert all(r["source"] == "devfolio" for r in records)


def test_known_non_hackathon_subdomains_are_excluded():
    soup = BeautifulSoup(FIXTURE_HTML, "html.parser")
    records = LiveDevfolioScraper().parse(soup)
    urls = {r["url"] for r in records}
    assert not any("guide." in u or "status." in u or "www." in u for u in urls)


def test_duplicate_links_are_deduplicated():
    soup = BeautifulSoup(FIXTURE_HTML, "html.parser")
    records = LiveDevfolioScraper().parse(soup)
    hackverse = [r for r in records if r["title"] == "Hackverse.2026"]
    assert len(hackverse) == 1


def test_no_hackathon_links_returns_empty_list():
    soup = BeautifulSoup("<html><body><a href='https://example.com'>x</a></body></html>", "html.parser")
    assert LiveDevfolioScraper().parse(soup) == []
