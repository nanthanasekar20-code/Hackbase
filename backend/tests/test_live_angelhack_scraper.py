"""
Unit test for LiveAngelHackScraper's HTML parsing logic, using a fixture
shaped like angelhack.com's real homepage markup (verified live): event
cards are `h2.elementor-heading-title` wrapped in an `<a href=".../event/
...">`; every other heading on the page (section titles, blog posts) has
no such wrapping link. Doesn't hit the network.
"""

from bs4 import BeautifulSoup

from app.scrapers.live_angelhack_scraper import LiveAngelHackScraper

FIXTURE_HTML = """
<html><body>
<div><h2 class="elementor-heading-title">Our services</h2></div>
<div><h2 class="elementor-heading-title">Latest Events</h2></div>
<div><a href="https://angelhack.com/event/building-with-ibm-bob/">
  <div><div><h2 class="elementor-heading-title">Building with IBM Bob Hackathon</h2></div></div>
</a></div>
<div><a href="https://angelhack.com/event/databricks-appquest/">
  <div><div><h2 class="elementor-heading-title">Databricks AppQuest</h2></div></div>
</a></div>
<div><h2 class="elementor-heading-title">News &amp; Insights</h2></div>
<div><a href="https://angelhack.com/blog/some-post/">
  <div><h2 class="elementor-heading-title">A blog post, not an event</h2></div>
</a></div>
</body></html>
"""


def test_parses_only_cards_linking_to_event_pages():
    soup = BeautifulSoup(FIXTURE_HTML, "html.parser")
    records = LiveAngelHackScraper().parse(soup)
    titles = {r["title"] for r in records}
    assert titles == {"Building with IBM Bob Hackathon", "Databricks AppQuest"}


def test_section_titles_and_blog_posts_are_excluded():
    soup = BeautifulSoup(FIXTURE_HTML, "html.parser")
    records = LiveAngelHackScraper().parse(soup)
    titles = {r["title"] for r in records}
    assert "Latest Events" not in titles
    assert "News & Insights" not in titles
    assert "A blog post, not an event" not in titles


def test_no_event_cards_returns_empty_list():
    soup = BeautifulSoup("<html><body><h2 class='elementor-heading-title'>Nothing here</h2></body></html>", "html.parser")
    assert LiveAngelHackScraper().parse(soup) == []
