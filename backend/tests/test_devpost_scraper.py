"""
Unit test for DevpostScraper's parsing/hydration logic, using a fixture
shaped like a real devpost.com/api/hackathons listing item (verified
live). _fetch_description() (the one real per-hackathon HTTP call) is
monkeypatched so this stays offline/fast — its own selector logic is a
single `#challenge-description` lookup, verified live against several
real hackathon pages (see the module docstring), not worth a second
fixture-parsing test here.
"""

import pytest

from app.scrapers.devpost_scraper import DevpostScraper

FIXTURE_LISTINGS = [
    {
        "id": 31609,
        "title": "InterWell Hack2.0",
        "url": "https://interwell-hack2-0.devpost.com/",
        "organization_name": "InternWell-SLIET",
        "themes": [{"id": 10, "name": "Communication"}, {"id": 6, "name": "Machine Learning/AI"}],
    },
    {
        "id": 31600,
        "title": "No Themes Hackathon",
        "url": "https://no-themes.devpost.com/",
        "organization_name": None,
        "themes": [],
    },
    # Real-world edge case: a malformed entry with no url.
    {"id": 99999, "title": "Missing URL", "url": "", "themes": []},
]


@pytest.fixture(autouse=True)
def _no_real_delay(monkeypatch):
    # The real scraper paces per-hackathon description fetches with a
    # polite sleep (see DETAIL_FETCH_DELAY_SECONDS) — not worth paying for
    # in tests that never make a real request anyway.
    monkeypatch.setattr("app.scrapers.devpost_scraper.time.sleep", lambda _seconds: None)


def test_parses_listing_fields_and_hydrates_description(monkeypatch):
    monkeypatch.setattr(DevpostScraper, "_fetch_description", lambda self, url: "A real About blurb.")
    records = DevpostScraper().parse(FIXTURE_LISTINGS)

    assert len(records) == 2  # the no-url entry is skipped
    first = records[0]
    assert first["title"] == "InterWell Hack2.0"
    assert first["description"] == "A real About blurb."
    assert first["organization"] == "InternWell-SLIET"
    assert first["source"] == "devpost"
    assert first["hackathon_name"] == "InterWell Hack2.0"
    assert first["external_id"] == "31609"
    assert first["category"] == "Communication"
    assert first["theme"] == "Communication, Machine Learning/AI"
    assert first["url"] == "https://interwell-hack2-0.devpost.com/"
    assert first["fetched_at"] is not None


def test_no_themes_gives_none_category_and_theme(monkeypatch):
    monkeypatch.setattr(DevpostScraper, "_fetch_description", lambda self, url: "")
    records = DevpostScraper().parse(FIXTURE_LISTINGS)
    no_themes = next(r for r in records if r["title"] == "No Themes Hackathon")
    assert no_themes["category"] is None
    assert no_themes["theme"] is None
    assert no_themes["organization"] is None


def test_skips_entries_with_no_url(monkeypatch):
    monkeypatch.setattr(DevpostScraper, "_fetch_description", lambda self, url: "x")
    records = DevpostScraper().parse(FIXTURE_LISTINGS)
    assert all(r["title"] != "Missing URL" for r in records)


def test_a_single_failing_description_fetch_does_not_lose_the_record(monkeypatch):
    """A real network hiccup on one hackathon's page shouldn't drop that
    hackathon from the run — just leave its description blank."""

    def _flaky(self, url):
        if "interwell" in url:
            raise RuntimeError("connection reset")
        return "fine"

    monkeypatch.setattr(DevpostScraper, "_fetch_description", _flaky)
    records = DevpostScraper().parse(FIXTURE_LISTINGS)

    interwell = next(r for r in records if r["title"] == "InterWell Hack2.0")
    assert interwell["description"] == ""  # honest blank, not dropped/fabricated
    other = next(r for r in records if r["title"] == "No Themes Hackathon")
    assert other["description"] == "fine"


def test_empty_listings_returns_empty_list():
    assert DevpostScraper().parse([]) == []
