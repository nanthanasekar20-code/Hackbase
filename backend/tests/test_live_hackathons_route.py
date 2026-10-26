"""
Tests for GET /api/v1/live-hackathons and its backing reader
(app/core/live_hackathons.py) — a plain read of
data/processed/live_hackathons.json, completely separate from the
problem-statement corpus. No auth required (same as /resources used to
be) — this is public info, like the rest of a hackathon listing site.
"""

import json

from fastapi.testclient import TestClient

import app.core.live_hackathons as live_hackathons_module
from app.main import app

client = TestClient(app)


def test_returns_honest_empty_feed_when_no_file_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(live_hackathons_module, "PROCESSED_PATH", tmp_path / "does-not-exist.json")
    live_hackathons_module.reset_cache()

    response = client.get("/api/v1/live-hackathons")
    assert response.status_code == 200
    body = response.json()
    assert body["hackathons"] == []
    assert body["count"] == 0
    assert body["updated_at"] is None


def test_returns_real_written_hackathons(tmp_path, monkeypatch):
    fake_path = tmp_path / "live_hackathons.json"
    fake_path.write_text(
        json.dumps(
            {
                "updated_at": "2026-10-03T00:00:00+00:00",
                "count": 1,
                "per_source_counts": {"devpost": 1},
                "hackathons": [
                    {"title": "Real Hackathon", "source": "devpost", "url": "https://example.devpost.com/"}
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(live_hackathons_module, "PROCESSED_PATH", fake_path)
    live_hackathons_module.reset_cache()

    response = client.get("/api/v1/live-hackathons")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["hackathons"][0]["title"] == "Real Hackathon"
    assert body["hackathons"][0]["url"] == "https://example.devpost.com/"


def test_cache_is_reused_until_reset(tmp_path, monkeypatch):
    fake_path = tmp_path / "live_hackathons.json"
    fake_path.write_text(json.dumps({"updated_at": None, "count": 0, "per_source_counts": {}, "hackathons": []}))
    monkeypatch.setattr(live_hackathons_module, "PROCESSED_PATH", fake_path)
    live_hackathons_module.reset_cache()

    first = live_hackathons_module.get_live_hackathons()
    # Overwrite the file without resetting the cache — should still see the old value.
    fake_path.write_text(
        json.dumps({"updated_at": "later", "count": 1, "per_source_counts": {}, "hackathons": [{"title": "x"}]})
    )
    second = live_hackathons_module.get_live_hackathons()
    assert first is second  # same cached dict object, not re-read

    live_hackathons_module.reset_cache()
    third = live_hackathons_module.get_live_hackathons()
    assert third["count"] == 1


# --- Excluding hackathons whose own deadline has clearly passed ---
#
# Real incident: the scheduled refresh (app/services/live_hackathons_job.py)
# only runs while the app process stays up, so a feed that was genuinely
# open when last scraped can sit stale for weeks on a dev machine, and
# several real entries' submission windows had already ended while still
# being served as "open". get_live_hackathons() now re-checks every
# parseable deadline against the real current date on every call, not just
# at scrape time.


def _write_feed(tmp_path, monkeypatch, hackathons):
    fake_path = tmp_path / "live_hackathons.json"
    fake_path.write_text(
        json.dumps({"updated_at": "2026-01-01T00:00:00Z", "count": len(hackathons), "per_source_counts": {}, "hackathons": hackathons})
    )
    monkeypatch.setattr(live_hackathons_module, "PROCESSED_PATH", fake_path)
    live_hackathons_module.reset_cache()


def _days_from_now(days):
    from datetime import datetime, timedelta, timezone

    return datetime.now(timezone.utc).date() + timedelta(days=days)


def _fmt(d):
    return d.strftime("%b %d, %Y")  # e.g. "Nov 12, 2026" — matches the real scrapers' shape


def test_excludes_a_hackathon_whose_single_date_deadline_has_passed(tmp_path, monkeypatch):
    past = _fmt(_days_from_now(-5))
    future = _fmt(_days_from_now(5))
    _write_feed(
        tmp_path,
        monkeypatch,
        [
            {"title": "Already Ended", "source": "devpost", "url": "https://a.devpost.com/", "deadline": past},
            {"title": "Still Open", "source": "devpost", "url": "https://b.devpost.com/", "deadline": future},
        ],
    )

    data = live_hackathons_module.get_live_hackathons()

    assert [h["title"] for h in data["hackathons"]] == ["Still Open"]
    assert data["count"] == 1


def test_keeps_a_cross_month_range_whose_end_is_still_in_the_future(tmp_path, monkeypatch):
    # e.g. the real "Oct 01 - Nov 12, 2026" shape — end date is what matters.
    end = _days_from_now(10)
    start_month = _days_from_now(-5).strftime("%b")
    deadline = f"{start_month} 01 - {end.strftime('%b %d')}, {end.year}"
    _write_feed(
        tmp_path, monkeypatch,
        [{"title": "Cross-Month Range", "source": "devpost", "url": "https://x.devpost.com/", "deadline": deadline}],
    )

    data = live_hackathons_module.get_live_hackathons()

    assert [h["title"] for h in data["hackathons"]] == ["Cross-Month Range"]


def test_excludes_a_same_month_range_that_has_fully_passed(tmp_path, monkeypatch):
    # e.g. the real "Oct 03 - 31, 2026" shape.
    end = _days_from_now(-3)
    deadline = f"{end.strftime('%b')} 01 - {end.day:02d}, {end.year}"
    _write_feed(
        tmp_path, monkeypatch,
        [{"title": "Ended Range", "source": "devpost", "url": "https://x.devpost.com/", "deadline": deadline}],
    )

    data = live_hackathons_module.get_live_hackathons()

    assert data["hackathons"] == []
    assert data["count"] == 0


def test_infers_a_sensible_year_for_a_deadline_with_no_year_at_all(tmp_path, monkeypatch):
    # e.g. the real MLH shape: "NOV 07 - 08" with no year in the string.
    future = _days_from_now(10)
    deadline = f"{future.strftime('%b').upper()} {future.day:02d} - {(future.day + 1):02d}"
    _write_feed(
        tmp_path, monkeypatch,
        [{"title": "No Year Given", "source": "mlh", "url": "https://x.mlh.io/", "deadline": deadline}],
    )

    data = live_hackathons_module.get_live_hackathons()

    assert [h["title"] for h in data["hackathons"]] == ["No Year Given"]


def test_never_excludes_a_hackathon_with_no_deadline_at_all(tmp_path, monkeypatch):
    # Most sources never capture a deadline (see e.g. live_taikai_scraper.py)
    # — absence of a date must never be treated as "ended".
    _write_feed(
        tmp_path, monkeypatch,
        [{"title": "No Deadline Captured", "source": "taikai", "url": "https://x.taikai.network/", "deadline": None}],
    )

    data = live_hackathons_module.get_live_hackathons()

    assert [h["title"] for h in data["hackathons"]] == ["No Deadline Captured"]


def test_never_excludes_on_an_unparseable_deadline_string(tmp_path, monkeypatch):
    _write_feed(
        tmp_path, monkeypatch,
        [{"title": "Weird Text", "source": "devpost", "url": "https://x.devpost.com/", "deadline": "Rolling admissions"}],
    )

    data = live_hackathons_module.get_live_hackathons()

    assert [h["title"] for h in data["hackathons"]] == ["Weird Text"]


def test_recomputes_per_source_counts_to_match_the_filtered_set(tmp_path, monkeypatch):
    past = _fmt(_days_from_now(-5))
    future = _fmt(_days_from_now(5))
    _write_feed(
        tmp_path, monkeypatch,
        [
            {"title": "Ended A", "source": "devpost", "url": "https://a.devpost.com/", "deadline": past},
            {"title": "Ended B", "source": "devpost", "url": "https://b.devpost.com/", "deadline": past},
            {"title": "Open", "source": "devpost", "url": "https://c.devpost.com/", "deadline": future},
            {"title": "No Date", "source": "mlh", "url": "https://d.mlh.io/", "deadline": None},
        ],
    )

    data = live_hackathons_module.get_live_hackathons()

    assert data["per_source_counts"] == {"devpost": 1, "mlh": 1}


def test_returns_the_identical_cached_object_when_nothing_is_excluded(tmp_path, monkeypatch):
    """Same byte-for-byte-identity guarantee the no-personalization path in
    app/rag/retriever.py makes — when filtering changes nothing, callers
    get the exact cached object back, not a rebuilt copy."""
    future = _fmt(_days_from_now(5))
    _write_feed(
        tmp_path, monkeypatch,
        [{"title": "Still Open", "source": "devpost", "url": "https://a.devpost.com/", "deadline": future}],
    )

    first = live_hackathons_module.get_live_hackathons()
    second = live_hackathons_module.get_live_hackathons()
    assert first is second


def test_route_surfaces_the_expiry_filtered_set(tmp_path, monkeypatch):
    past = _fmt(_days_from_now(-5))
    future = _fmt(_days_from_now(5))
    _write_feed(
        tmp_path, monkeypatch,
        [
            {"title": "Already Ended", "source": "devpost", "url": "https://a.devpost.com/", "deadline": past},
            {"title": "Still Open", "source": "devpost", "url": "https://b.devpost.com/", "deadline": future},
        ],
    )

    response = client.get("/api/v1/live-hackathons")

    body = response.json()
    assert [h["title"] for h in body["hackathons"]] == ["Still Open"]
    assert body["count"] == 1


# --- Optional source/search filters (frontend/src/pages/LiveHackathons.jsx's
# fuller listing) — additive only; see the route's own docstring for why
# `per_source_counts` always stays unfiltered.


def _write_multi_source_feed(tmp_path, monkeypatch):
    fake_path = tmp_path / "live_hackathons.json"
    fake_path.write_text(
        json.dumps(
            {
                "updated_at": "2026-10-07T00:00:00+00:00",
                "count": 3,
                "per_source_counts": {"devpost": 2, "mlh": 1},
                "hackathons": [
                    {"title": "AI Buildathon", "source": "devpost", "url": "https://a.devpost.com/"},
                    {"title": "Climate Hack", "source": "devpost", "url": "https://b.devpost.com/"},
                    {"title": "AI for Health", "source": "mlh", "url": "https://c.mlh.io/"},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(live_hackathons_module, "PROCESSED_PATH", fake_path)
    live_hackathons_module.reset_cache()


def test_no_params_returns_the_exact_same_payload_as_before_filters_existed(tmp_path, monkeypatch):
    _write_multi_source_feed(tmp_path, monkeypatch)
    response = client.get("/api/v1/live-hackathons")
    body = response.json()
    assert body["count"] == 3
    assert len(body["hackathons"]) == 3
    assert body["per_source_counts"] == {"devpost": 2, "mlh": 1}


def test_source_filter_narrows_hackathons_and_recomputes_count(tmp_path, monkeypatch):
    _write_multi_source_feed(tmp_path, monkeypatch)
    response = client.get("/api/v1/live-hackathons", params={"source": "mlh"})
    body = response.json()
    assert body["count"] == 1
    assert [h["title"] for h in body["hackathons"]] == ["AI for Health"]
    # Source breakdown stays the real, unfiltered picture — it's what
    # builds the filter's own options, not something that should shrink
    # to only the currently-selected source.
    assert body["per_source_counts"] == {"devpost": 2, "mlh": 1}


def test_search_filter_matches_title_case_insensitively(tmp_path, monkeypatch):
    _write_multi_source_feed(tmp_path, monkeypatch)
    response = client.get("/api/v1/live-hackathons", params={"search": "ai"})
    body = response.json()
    assert body["count"] == 2
    assert {h["title"] for h in body["hackathons"]} == {"AI Buildathon", "AI for Health"}


def test_source_and_search_filters_combine(tmp_path, monkeypatch):
    _write_multi_source_feed(tmp_path, monkeypatch)
    response = client.get("/api/v1/live-hackathons", params={"source": "devpost", "search": "climate"})
    body = response.json()
    assert body["count"] == 1
    assert body["hackathons"][0]["title"] == "Climate Hack"


def test_filters_returning_nothing_is_an_honest_empty_list_not_an_error(tmp_path, monkeypatch):
    _write_multi_source_feed(tmp_path, monkeypatch)
    response = client.get("/api/v1/live-hackathons", params={"search": "nonexistent-topic"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["hackathons"] == []
