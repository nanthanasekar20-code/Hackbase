"""
Unit test for LiveTaikaiScraper's HTML parsing logic, using a fixture
shaped like Taikai's real rendered listing (verified live): each card is
an `<a href="/en/<org>/hackathons/<slug>/">` whose cover `<img alt="...">`
carries the clean title (the link's own innerText mixes in status/stat
counts with no reliable separator). Doesn't hit the network.
"""

from bs4 import BeautifulSoup

from app.scrapers.live_taikai_scraper import LiveTaikaiScraper

FIXTURE_HTML = """
<html><body>
<a href="/en/spacexai/hackathons/spacexai-digital-transformation-lab/">
  <div><img alt="SpaceXAI Digital Transformation Lab" src="cover.jpg" /></div>
  Registration\\n7\\nSpaceXAI Digital Transformation Lab\\nPortuguese SMEs...
</a>
<a href="/en/eclipse-foundation/hackathons/veles-hack-2026/">
  <div><img alt="Veles Hack 2026" src="cover2.jpg" /></div>
  Registration open\\n89\\n10\\nVeles Hack 2026\\nRiding the Edge...
</a>
<a href="/auth/login">
  <div><img alt="Not a hackathon card" src="x.jpg" /></div>
</a>
<a href="/en/no-image/hackathons/no-image-hack/">No image here, should be skipped</a>
</body></html>
"""


def test_parses_title_from_cover_image_alt():
    soup = BeautifulSoup(FIXTURE_HTML, "html.parser")
    records = LiveTaikaiScraper().parse(soup)
    titles = {r["title"] for r in records}
    assert titles == {"SpaceXAI Digital Transformation Lab", "Veles Hack 2026"}


def test_resolves_relative_urls_to_absolute():
    soup = BeautifulSoup(FIXTURE_HTML, "html.parser")
    records = LiveTaikaiScraper().parse(soup)
    veles = next(r for r in records if r["title"] == "Veles Hack 2026")
    assert veles["url"] == "https://taikai.network/en/eclipse-foundation/hackathons/veles-hack-2026/"
    assert veles["source"] == "taikai"


def test_non_hackathon_links_are_excluded():
    soup = BeautifulSoup(FIXTURE_HTML, "html.parser")
    records = LiveTaikaiScraper().parse(soup)
    assert all("hackathons" in r["url"] for r in records)


def test_card_without_image_is_skipped():
    soup = BeautifulSoup(FIXTURE_HTML, "html.parser")
    records = LiveTaikaiScraper().parse(soup)
    assert all(r["title"] != "No image here, should be skipped" for r in records)
