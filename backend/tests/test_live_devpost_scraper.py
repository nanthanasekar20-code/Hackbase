"""
Unit test for LiveDevpostScraper's JSON parsing logic, using a fixture
shaped like a real response from devpost.com/api/hackathons?status[]=open
(verified live). Doesn't hit the network — fetch() is a thin wrapper
around parse().
"""

from app.scrapers.live_devpost_scraper import LiveDevpostScraper

FIXTURE_PAYLOAD = {
    "hackathons": [
        {
            "id": 31609,
            "title": "InterWell Hack2.0",
            "url": "https://interwell-hack2-0.devpost.com/",
            "submission_period_dates": "Oct 03 - 31, 2026",
            "open_state": "open",
        },
        {
            "id": 31557,
            "title": "MATLAB in Space",
            "url": "https://matlab-in-space.devpost.com/",
            "submission_period_dates": "Oct 03, 2026",
            "open_state": "open",
        },
        # Real-world edge case: a malformed/incomplete entry with no url.
        {"id": 99999, "title": "Missing URL", "url": "", "submission_period_dates": "Nov 2026"},
    ]
}


def test_parses_title_url_and_deadline():
    records = LiveDevpostScraper().parse(FIXTURE_PAYLOAD)
    assert len(records) == 2
    assert records[0]["title"] == "InterWell Hack2.0"
    assert records[0]["url"] == "https://interwell-hack2-0.devpost.com/"
    assert records[0]["source"] == "devpost"
    assert records[0]["deadline"] == "Oct 03 - 31, 2026"


def test_skips_entries_with_no_url():
    records = LiveDevpostScraper().parse(FIXTURE_PAYLOAD)
    assert all(r["title"] != "Missing URL" for r in records)


def test_empty_payload_returns_empty_list():
    assert LiveDevpostScraper().parse({"hackathons": []}) == []
    assert LiveDevpostScraper().parse({}) == []
