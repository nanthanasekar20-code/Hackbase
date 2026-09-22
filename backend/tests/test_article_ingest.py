"""
Tests for app.scrapers.article_ingest.

Only extract_from_article_url()'s inner generate_json() call and
fetch_github_problems()'s/fetch_github_index_entries()'s requests.get()
calls actually touch the network/Gemini — every test here monkeypatches
those, so nothing real is fetched or billed. The GitHub-path regexes are
also checked against real, previously-verified fixture text (mirroring
the actual repo's INDEX.md/file structure), not invented shapes.
"""

import json

import pytest

import app.scrapers.article_ingest as article_ingest
from app.rag.gemini_client import GeminiUnavailableError

INDEX_FIXTURE = """\
# INDEX — Hackathon Problem Statements

## By Track

### 🌍 Global South Impact (2 problems)

| # | Problem | File | Build Time | Tags |
|---|---------|------|-----------|------|
| 01 | Maternal Health Risk Stratification | [global-south-impact/maternal-health-risk-stratification.md](global-south-impact/maternal-health-risk-stratification.md) | 6-8mo | health, maternal, ML, offline |
| 02 | Public Procurement Fraud Detection | [global-south-impact/public-procurement-fraud-detection.md](global-south-impact/public-procurement-fraud-detection.md) | 5-7mo | governance, anti-corruption, GNN |

### 🇺🇸 US Civic Tech (1 problems)

| # | Problem | File | Build Time | Tags |
|---|---------|------|-----------|------|
| 01 | CivicFeed — Public Comment Intelligence | [us-civic-tech/civicfeed-public-comment-intelligence.md](us-civic-tech/civicfeed-public-comment-intelligence.md) | 6-8w | civic-tech, government, LLM |
"""

PROBLEM_FILE_FIXTURE = """\
---
track: global-south-impact
status: published
---

# Maternal Health Risk Stratification for Low-Resource Settings

> Public Health | Maternal Health — 6-8 month build

## The Problem

Every day, approximately 712 women die from preventable causes related to pregnancy and childbirth.
Existing risk scores are paper-based and static.

## Why Existing Solutions Fail

| Solution | Gap |
|---|---|
| WHO Maternity Risk Score | Static checklist |

## What to Build

- An ensemble ML pipeline
"""


def test_parse_github_index_extracts_all_rows_grouped_by_track():
    entries = article_ingest._parse_github_index(INDEX_FIXTURE)

    assert len(entries) == 3
    assert entries[0] == {
        "title": "Maternal Health Risk Stratification",
        "path": "global-south-impact/maternal-health-risk-stratification.md",
        "track": "Global South Impact",
        "tags": "health, maternal, ML, offline",
    }
    assert entries[2]["track"] == "US Civic Tech"
    assert entries[2]["title"] == "CivicFeed — Public Comment Intelligence"


def test_parse_github_problem_file_extracts_title_and_problem_section_only():
    title, statement = article_ingest._parse_github_problem_file(PROBLEM_FILE_FIXTURE, fallback_title="fallback")

    assert title == "Maternal Health Risk Stratification for Low-Resource Settings"
    assert "712 women die" in statement
    # Must stop at the next "##" heading, not bleed into later sections.
    assert "Why Existing Solutions Fail" not in statement
    assert "ensemble ML pipeline" not in statement


def test_parse_github_problem_file_falls_back_when_structure_is_missing():
    title, statement = article_ingest._parse_github_problem_file("just some plain text, no headings", "Fallback Title")
    assert title == "Fallback Title"
    assert statement == "just some plain text, no headings"


def test_fetch_github_problems_builds_real_problem_shaped_records(monkeypatch):
    entries = article_ingest._parse_github_index(INDEX_FIXTURE)

    class _FakeResponse:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            pass

    def fake_get(url, headers=None, timeout=None):
        assert "maternal-health-risk-stratification.md" in url
        return _FakeResponse(PROBLEM_FILE_FIXTURE)

    monkeypatch.setattr(article_ingest.requests, "get", fake_get)

    records = article_ingest.fetch_github_problems(
        entries, paths={"global-south-impact/maternal-health-risk-stratification.md"}
    )

    assert len(records) == 1
    r = records[0]
    assert r["title"] == "Maternal Health Risk Stratification for Low-Resource Settings"
    assert r["source"] == "article"
    assert r["category"] == "Global South Impact"
    assert r["theme"] == "health, maternal, ML, offline"
    assert r["external_id"] == "global-south-impact/maternal-health-risk-stratification"
    assert r["url"].endswith("global-south-impact/maternal-health-risk-stratification.md")
    assert "712 women die" in r["description"]


def test_fetch_github_problems_paths_filter_skips_unrequested_entries(monkeypatch):
    entries = article_ingest._parse_github_index(INDEX_FIXTURE)
    calls = []

    class _FakeResponse:
        text = PROBLEM_FILE_FIXTURE

        def raise_for_status(self):
            pass

    def fake_get(url, headers=None, timeout=None):
        calls.append(url)
        return _FakeResponse()

    monkeypatch.setattr(article_ingest.requests, "get", fake_get)

    records = article_ingest.fetch_github_problems(entries, paths=set())
    assert records == []
    assert calls == []  # nothing fetched when the filter excludes every entry


def test_parse_extraction_response_accepts_a_well_formed_array():
    raw = json.dumps(
        [
            {"title": "Fake News Tracker", "statement": "Detect fake news spreading online.", "domain_guess": "NLP"},
            {"title": "No Domain Guess", "statement": "A problem with no domain.", "domain_guess": None},
        ]
    )
    records = article_ingest._parse_extraction_response(raw, "https://example.com/blog")

    assert len(records) == 2
    assert records[0]["title"] == "Fake News Tracker"
    assert records[0]["description"] == "Detect fake news spreading online."
    assert records[0]["theme"] == "NLP"
    assert records[0]["source"] == "article"
    assert records[0]["hackathon_name"] == "example.com"
    assert records[0]["url"] == "https://example.com/blog"
    assert records[1]["theme"] is None


def test_parse_extraction_response_handles_empty_list_honestly():
    # The explicit, expected "found nothing real" answer — must NOT be
    # treated as an error or padded with anything invented.
    assert article_ingest._parse_extraction_response("[]", "https://example.com") == []


def test_parse_extraction_response_skips_malformed_items_without_crashing():
    raw = json.dumps(
        [
            {"title": "Good One", "statement": "A real statement."},
            {"title": "Missing statement field"},
            "not even a dict",
            {"statement": "Missing title field"},
        ]
    )
    records = article_ingest._parse_extraction_response(raw, "https://example.com")
    assert len(records) == 1
    assert records[0]["title"] == "Good One"


def test_parse_extraction_response_handles_invalid_json_gracefully():
    assert article_ingest._parse_extraction_response("not json at all {{{", "https://example.com") == []


def test_extract_from_article_url_sends_real_page_text_to_gemini(monkeypatch):
    monkeypatch.setattr(article_ingest, "_fetch_page_text", lambda url: "Some real extracted page text.")
    monkeypatch.setattr(article_ingest, "get_gemini_model", lambda: object())

    captured_prompts = []

    def fake_generate_json(model, prompt, **kwargs):
        captured_prompts.append(prompt)
        return json.dumps([{"title": "T", "statement": "S", "domain_guess": None}])

    monkeypatch.setattr(article_ingest, "generate_json", fake_generate_json)

    records = article_ingest.extract_from_article_url("https://example.com/page")

    assert len(records) == 1
    assert "Some real extracted page text." in captured_prompts[0]
    assert "only return" in captured_prompts[0].lower() or "explicitly described" in captured_prompts[0].lower()


def test_try_extract_reports_success_with_a_genuine_empty_result(monkeypatch):
    # A page that Gemini actually checked and found nothing real on —
    # succeeded=True is what tells run() this must NOT be retried forever.
    monkeypatch.setattr(article_ingest, "_fetch_page_text", lambda url: "Some real page text, no problems on it.")
    monkeypatch.setattr(article_ingest, "get_gemini_model", lambda: object())
    monkeypatch.setattr(article_ingest, "generate_json", lambda model, prompt, **kwargs: "[]")

    records, succeeded = article_ingest._try_extract_from_article_url("https://example.com/empty-but-real")
    assert records == []
    assert succeeded is True


def test_try_extract_reports_failure_when_gemini_unavailable(monkeypatch):
    monkeypatch.setattr(article_ingest, "_fetch_page_text", lambda url: "Some text.")
    monkeypatch.setattr(article_ingest, "get_gemini_model", lambda: object())

    def fake_generate_json(model, prompt, **kwargs):
        raise GeminiUnavailableError("quota exhausted")

    monkeypatch.setattr(article_ingest, "generate_json", fake_generate_json)

    records, succeeded = article_ingest._try_extract_from_article_url("https://example.com/page")
    assert records == []
    assert succeeded is False  # must be retried next run, not treated as "checked, nothing there"


def test_try_extract_reports_failure_when_page_fetch_raises(monkeypatch):
    import requests

    def fake_fetch(url):
        raise requests.RequestException("connection reset")

    monkeypatch.setattr(article_ingest, "_fetch_page_text", fake_fetch)
    records, succeeded = article_ingest._try_extract_from_article_url("https://example.com/broken")
    assert records == []
    assert succeeded is False


def test_extract_from_article_url_returns_empty_list_when_gemini_unavailable(monkeypatch):
    monkeypatch.setattr(article_ingest, "_fetch_page_text", lambda url: "Some text.")
    monkeypatch.setattr(article_ingest, "get_gemini_model", lambda: object())

    def fake_generate_json(model, prompt, **kwargs):
        raise GeminiUnavailableError("quota exhausted")

    monkeypatch.setattr(article_ingest, "generate_json", fake_generate_json)

    assert article_ingest.extract_from_article_url("https://example.com/page") == []


def test_extract_from_article_url_skips_gemini_call_when_page_has_no_text(monkeypatch):
    monkeypatch.setattr(article_ingest, "_fetch_page_text", lambda url: "   ")
    called = []
    monkeypatch.setattr(article_ingest, "get_gemini_model", lambda: called.append(1))

    assert article_ingest.extract_from_article_url("https://example.com/empty") == []
    assert called == []  # never even tried to call Gemini for a page with nothing on it


class _FakeTrackerCM:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def log_metric(self, *a, **k):
        pass


@pytest.fixture
def isolated_run(tmp_path, monkeypatch):
    """Points OUTPUT_PATH/STATE_PATH at tmp files and stubs out track_run
    so run() tests never touch the real data/raw/ directory or real
    mlflow."""
    monkeypatch.setattr(article_ingest, "OUTPUT_PATH", tmp_path / "article_ingest.json")
    monkeypatch.setattr(article_ingest, "STATE_PATH", tmp_path / "article_ingest_state.json")
    monkeypatch.setattr(article_ingest, "track_run", lambda *a, **k: _FakeTrackerCM())
    return tmp_path


def test_run_writes_records_from_both_paths_on_a_fresh_run(monkeypatch, isolated_run):
    monkeypatch.setattr(
        article_ingest,
        "fetch_github_index_entries",
        lambda: [{"title": "GH Problem", "path": "track/gh-problem.md", "track": "Track", "tags": "t"}],
    )
    monkeypatch.setattr(
        article_ingest,
        "fetch_github_problems",
        lambda entries, paths=None: [
            {"title": "GH Problem", "description": "d", "source": "article", "url": article_ingest.GITHUB_BLOB_BASE + "/track/gh-problem.md"}
        ],
    )

    call_count = {"n": 0}

    def fake_try_extract(url):
        call_count["n"] += 1
        return [{"title": f"Item from {url}", "description": "d", "source": "article", "url": url}], True

    monkeypatch.setattr(article_ingest, "_try_extract_from_article_url", fake_try_extract)

    merged = article_ingest.run()

    assert call_count["n"] == len(article_ingest.ARTICLE_URLS)
    assert len(merged) == len(article_ingest.ARTICLE_URLS) + 1  # every article URL's item + the one GitHub file
    assert article_ingest.OUTPUT_PATH.exists()


def test_run_is_idempotent_and_makes_no_calls_for_already_present_urls(monkeypatch, isolated_run):
    monkeypatch.setattr(
        article_ingest,
        "fetch_github_index_entries",
        lambda: [{"title": "GH Problem", "path": "track/gh-problem.md", "track": "Track", "tags": "t"}],
    )
    gh_url = article_ingest.GITHUB_BLOB_BASE + "/track/gh-problem.md"
    monkeypatch.setattr(
        article_ingest,
        "fetch_github_problems",
        lambda entries, paths=None: [{"title": "GH Problem", "description": "d", "source": "article", "url": gh_url}],
    )
    call_count = {"n": 0}

    def fake_try_extract(url):
        call_count["n"] += 1
        return [{"title": f"Item from {url}", "description": "d", "source": "article", "url": url}], True

    monkeypatch.setattr(article_ingest, "_try_extract_from_article_url", fake_try_extract)

    first = article_ingest.run()
    assert call_count["n"] == len(article_ingest.ARTICLE_URLS)

    # Second run: every URL (article + GitHub) is already in the output —
    # must make zero new extraction calls (real quota-consuming calls) and
    # zero new GitHub file fetches, and must not duplicate any record.
    monkeypatch.setattr(
        article_ingest,
        "fetch_github_problems",
        lambda entries, paths=None: (_ for _ in ()).throw(AssertionError("should not be called again")),
    )
    second = article_ingest.run()

    assert call_count["n"] == len(article_ingest.ARTICLE_URLS)  # unchanged — no new calls
    assert len(second) == len(first)  # no duplicates


def test_run_does_not_re_ask_gemini_about_a_page_genuinely_found_empty(monkeypatch, isolated_run):
    # The exact bug this was built to catch: a page Gemini genuinely
    # checked and found nothing on yields zero records, same as a page
    # that failed to fetch — without the success flag, run() can't tell
    # them apart and would re-call Gemini on the empty-but-real page
    # forever. This locks in that succeeded=True must stop that.
    monkeypatch.setattr(article_ingest, "fetch_github_index_entries", lambda: [])
    monkeypatch.setattr(article_ingest, "fetch_github_problems", lambda entries, paths=None: [])

    call_count = {"n": 0}

    def fake_try_extract(url):
        call_count["n"] += 1
        return [], True  # every page genuinely has nothing on it

    monkeypatch.setattr(article_ingest, "_try_extract_from_article_url", fake_try_extract)

    article_ingest.run()
    assert call_count["n"] == len(article_ingest.ARTICLE_URLS)

    article_ingest.run()
    assert call_count["n"] == len(article_ingest.ARTICLE_URLS)  # unchanged on the second run


def test_run_retries_a_url_that_failed_but_not_ones_that_succeeded(monkeypatch, isolated_run):
    monkeypatch.setattr(article_ingest, "fetch_github_index_entries", lambda: [])
    monkeypatch.setattr(article_ingest, "fetch_github_problems", lambda entries, paths=None: [])

    failing_url = article_ingest.ARTICLE_URLS[0]
    call_log = []

    def fake_try_extract(url):
        call_log.append(url)
        if url == failing_url:
            return [], False  # transient failure — must be retried
        return [{"title": "ok", "description": "d", "source": "article", "url": url}], True

    monkeypatch.setattr(article_ingest, "_try_extract_from_article_url", fake_try_extract)

    article_ingest.run()
    assert call_log.count(failing_url) == 1

    call_log.clear()
    article_ingest.run()
    # Only the previously-failed URL should be attempted again.
    assert call_log == [failing_url]


def test_run_force_redoes_everything_and_drops_stale_records_first(monkeypatch, isolated_run):
    monkeypatch.setattr(article_ingest, "fetch_github_index_entries", lambda: [])
    monkeypatch.setattr(article_ingest, "fetch_github_problems", lambda entries, paths=None: [])

    call_count = {"n": 0}

    def fake_try_extract(url):
        call_count["n"] += 1
        return [{"title": f"v{call_count['n']}", "description": "d", "source": "article", "url": url}], True

    monkeypatch.setattr(article_ingest, "_try_extract_from_article_url", fake_try_extract)

    first = article_ingest.run()
    assert call_count["n"] == len(article_ingest.ARTICLE_URLS)

    second = article_ingest.run(force=True)
    assert call_count["n"] == 2 * len(article_ingest.ARTICLE_URLS)  # re-fetched every URL
    assert len(second) == len(first)  # old versions replaced, not appended alongside new ones
