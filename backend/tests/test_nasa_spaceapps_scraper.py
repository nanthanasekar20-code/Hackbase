"""
Unit tests for NasaSpaceAppsScraper, using small fixtures shaped like
the real rendered pages (verified live): the listing page links to each
challenge's own `/<year>/challenges/<slug>/` page, and each challenge
page has an <h1> title plus Summary/Background/Objectives/Potential
Considerations <h2> sections and a "Subjects" tag list. Doesn't hit the
network — these are given already-rendered HTML, the same shape
playwright_utils.render_html() would hand to fetch()/parse().
"""

from bs4 import BeautifulSoup

from app.scrapers.nasa_spaceapps_scraper import NasaSpaceAppsScraper

LISTING_HTML = """
<html><body>
<a href="/2025/challenges/meteor-madness/">Meteor Madness</a>
<a href="/2025/challenges/sharks-from-space/">Sharks from Space</a>
<a href="/2025/challenges/meteor-madness/">Meteor Madness</a>
<a href="/2025/challenges/">All challenges</a>
<a href="/2026/challenges/">2026 challenges</a>
<a href="/about">About</a>
</body></html>
"""

DETAIL_HTML = """
<html><body>
<h1>Meteor Madness</h1>
<h3>Subjects</h3>
<div><a>Astrophysics</a><a>Coding</a><a>Disaster Response</a></div>
<div class="content">
  <h2>Summary</h2>
  <p>A newly identified near-Earth asteroid poses a potential threat to Earth.</p>
  <h2>Background</h2>
  <p>The discovery highlights the ongoing risk of celestial objects colliding with our planet.</p>
  <h2>Objectives</h2>
  <p>Develop an interactive visualization and simulation tool.</p>
  <h2>Potential Considerations</h2>
  <p>Consider accessibility for non-experts while retaining technical depth.</p>
</div>
</body></html>
"""

DETAIL_HTML_NO_SECTIONS = """
<html><body>
<h1>Create Your Own Challenge</h1>
<div class="content"></div>
</body></html>
"""


def test_extracts_unique_challenge_urls_from_listing():
    soup = BeautifulSoup(LISTING_HTML, "html.parser")
    scraper = NasaSpaceAppsScraper(year="2025")
    urls = scraper._extract_challenge_urls(soup)
    assert urls == [
        "https://www.spaceappschallenge.org/2025/challenges/meteor-madness/",
        "https://www.spaceappschallenge.org/2025/challenges/sharks-from-space/",
    ]


def test_parses_title_and_all_four_sections_into_description():
    soup = BeautifulSoup(DETAIL_HTML, "html.parser")
    record = NasaSpaceAppsScraper(year="2025").parse(soup, "https://www.spaceappschallenge.org/2025/challenges/meteor-madness/")

    assert record["title"] == "Meteor Madness"
    assert "Summary:" in record["description"]
    assert "Background:" in record["description"]
    assert "Objectives:" in record["description"]
    assert "Potential Considerations:" in record["description"]
    assert "near-Earth asteroid" in record["description"]
    assert record["source"] == "nasa_spaceapps"
    assert record["organization"] == "NASA"
    assert record["hackathon_name"] == "NASA Space Apps Challenge 2025"
    assert record["external_id"] == "nasa_spaceapps:meteor-madness"
    assert record["theme"] == "Astrophysics, Coding, Disaster Response"
    assert record["url"].endswith("/meteor-madness/")


def test_skips_a_page_with_no_section_text():
    soup = BeautifulSoup(DETAIL_HTML_NO_SECTIONS, "html.parser")
    record = NasaSpaceAppsScraper(year="2025").parse(soup, "https://www.spaceappschallenge.org/2025/challenges/create-your-own-challenge/")
    assert record is None


def test_skips_a_page_with_no_title():
    soup = BeautifulSoup("<html><body><div>no h1 here</div></body></html>", "html.parser")
    assert NasaSpaceAppsScraper(year="2025").parse(soup, "https://example.com/x") is None
