"""
Unit test for LiveHack2SkillScraper's HTML parsing logic, using a
fixture shaped like Hack2Skill's real rendered homepage (verified live):
each card's `<a href=".../event/...">` text is just the status/button
label ("Register Now" vs. "Registration closed"), with the real title in
a heading a few levels up. Only currently-open cards should be kept.
Doesn't hit the network.
"""

from bs4 import BeautifulSoup

from app.scrapers.live_hack2skill_scraper import LiveHack2SkillScraper

FIXTURE_HTML = """
<html><body>
<div><div><div><div>
  <h3>Builder Pop-Up</h3>
  <a href="https://hack2skill.com/event/builderpopup/">Register Now</a>
</div></div></div></div>
<div><div><div><div>
  <h3>AI for Impact</h3>
  <a href="https://hack2skill.com/event/aiforimpact_reg">Registration closed</a>
</div></div></div></div>
</body></html>
"""

NO_HEADING_ANYWHERE_HTML = """
<html><body>
<div><div><div><div>
  <a href="https://hack2skill.com/event/no-title-anywhere/">Register Now</a>
</div></div></div></div>
</body></html>
"""


def test_parses_only_currently_open_cards():
    soup = BeautifulSoup(FIXTURE_HTML, "html.parser")
    records = LiveHack2SkillScraper().parse(soup)
    titles = {r["title"] for r in records}
    assert titles == {"Builder Pop-Up"}
    assert all(r["source"] == "hack2skill" for r in records)


def test_closed_registrations_are_excluded():
    soup = BeautifulSoup(FIXTURE_HTML, "html.parser")
    records = LiveHack2SkillScraper().parse(soup)
    assert all(r["title"] != "AI for Impact" for r in records)


def test_card_with_no_heading_anywhere_is_skipped():
    soup = BeautifulSoup(NO_HEADING_ANYWHERE_HTML, "html.parser")
    assert LiveHack2SkillScraper().parse(soup) == []


def test_no_open_cards_returns_empty_list():
    soup = BeautifulSoup("<html><body>nothing</body></html>", "html.parser")
    assert LiveHack2SkillScraper().parse(soup) == []
