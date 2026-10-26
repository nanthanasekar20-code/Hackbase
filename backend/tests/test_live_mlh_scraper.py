"""
Unit test for LiveMLHScraper's HTML parsing logic, using a fixture shaped
like the real embedded Inertia.js payload on www.mlh.com/seasons/{year}/
events (verified live: `<script data-page="app" type="application/json">`
carrying `props.upcomingEvents`). Doesn't hit the network.
"""

import json

from app.scrapers.live_mlh_scraper import LiveMLHScraper

FIXTURE_PAYLOAD = {
    "component": "EventsListing",
    "props": {
        "upcomingEvents": [
            {
                "name": "HACK.COMS 2026",
                "url": "/events/hack-coms-2f/prizes",
                "websiteUrl": "https://events.mlh.io/events/14418-hack-coms-2026",
                "dateRange": "NOV 07 - 08",
            },
            {
                "name": "No Website URL Event",
                "url": "/events/no-website/prizes",
                "websiteUrl": None,
                "dateRange": "DEC 01 - 02",
            },
            {"name": "", "url": "/events/blank-name/prizes", "websiteUrl": "https://example.com"},
        ],
        "pastEvents": [{"name": "Old Hackathon", "url": "/events/old/prizes"}],
    },
}

FIXTURE_HTML = f"""
<html><body>
<script data-page="app" type="application/json">{json.dumps(FIXTURE_PAYLOAD)}</script>
</body></html>
"""


def test_parses_upcoming_events_preferring_website_url():
    records = LiveMLHScraper().parse(FIXTURE_HTML)
    assert len(records) == 2  # blank-name entry skipped, no-website falls back to relative url
    assert records[0]["title"] == "HACK.COMS 2026"
    assert records[0]["url"] == "https://events.mlh.io/events/14418-hack-coms-2026"
    assert records[0]["source"] == "mlh"
    assert records[0]["deadline"] == "NOV 07 - 08"


def test_falls_back_to_relative_url_when_no_website_url():
    records = LiveMLHScraper().parse(FIXTURE_HTML)
    fallback = next(r for r in records if r["title"] == "No Website URL Event")
    assert fallback["url"] == "https://www.mlh.com/events/no-website/prizes"


def test_ignores_past_events():
    records = LiveMLHScraper().parse(FIXTURE_HTML)
    assert all(r["title"] != "Old Hackathon" for r in records)


def test_missing_payload_returns_empty_list():
    assert LiveMLHScraper().parse("<html><body>no payload here</body></html>") == []


def test_malformed_json_payload_returns_empty_list():
    broken = '<script data-page="app" type="application/json">{not valid json</script>'
    assert LiveMLHScraper().parse(broken) == []
