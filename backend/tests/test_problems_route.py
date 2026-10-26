"""
Tests for GET /api/v1/problems/random and GET /api/v1/problems — both
plain, non-RAG reads over data/processed/problems.json via
app.core.corpus.get_all_problems(). No vector search/Chroma involved, so
these use a fake corpus file + corpus_module.reset_cache(), same pattern
as the favorites tests' fake problems.json (tests/test_auth.py).
"""

import json

from fastapi.testclient import TestClient

import app.core.corpus as corpus_module
from app.main import app

client = TestClient(app)


def _write_fake_corpus(tmp_path, monkeypatch, problems):
    fake_path = tmp_path / "problems.json"
    fake_path.write_text(json.dumps(problems), encoding="utf-8")
    monkeypatch.setattr(corpus_module, "PROCESSED_PATH", fake_path)
    corpus_module.reset_cache()


def _problem(id_, **overrides):
    base = {"id": id_, "title": f"Problem {id_}", "source": "sih", "summary": "A summary.", "domain": ["AI/ML"]}
    base.update(overrides)
    return base


# --- /problems/random ---


def test_random_returns_requested_count(tmp_path, monkeypatch):
    _write_fake_corpus(tmp_path, monkeypatch, [_problem(str(i)) for i in range(10)])
    resp = client.get("/api/v1/problems/random", params={"count": 4})
    assert resp.status_code == 200
    assert len(resp.json()["problems"]) == 4


def test_random_never_exceeds_pool_size(tmp_path, monkeypatch):
    _write_fake_corpus(tmp_path, monkeypatch, [_problem(str(i)) for i in range(3)])
    resp = client.get("/api/v1/problems/random", params={"count": 10})
    assert resp.status_code == 200
    assert len(resp.json()["problems"]) == 3  # never duplicates to pad out to `count`


def test_random_defaults_to_six(tmp_path, monkeypatch):
    _write_fake_corpus(tmp_path, monkeypatch, [_problem(str(i)) for i in range(10)])
    resp = client.get("/api/v1/problems/random")
    assert resp.status_code == 200
    assert len(resp.json()["problems"]) == 6


def test_random_is_genuinely_reshuffled_across_calls(tmp_path, monkeypatch):
    # 50 items and 10 draws of 10 makes a same-order coincidence astronomically
    # unlikely, so this is a real (not flaky-in-practice) assertion that
    # consecutive calls aren't a fixed/cached slice.
    _write_fake_corpus(tmp_path, monkeypatch, [_problem(str(i)) for i in range(50)])
    draws = [
        tuple(p["id"] for p in client.get("/api/v1/problems/random", params={"count": 10}).json()["problems"])
        for _ in range(10)
    ]
    assert len(set(draws)) > 1


def test_random_rejects_count_above_the_cap(tmp_path, monkeypatch):
    _write_fake_corpus(tmp_path, monkeypatch, [_problem(str(i)) for i in range(5)])
    resp = client.get("/api/v1/problems/random", params={"count": 999})
    assert resp.status_code == 422


def test_random_on_empty_corpus_returns_empty_list_not_an_error(tmp_path, monkeypatch):
    _write_fake_corpus(tmp_path, monkeypatch, [])
    resp = client.get("/api/v1/problems/random")
    assert resp.status_code == 200
    assert resp.json()["problems"] == []


# --- /problems ---


def test_list_paginates(tmp_path, monkeypatch):
    _write_fake_corpus(tmp_path, monkeypatch, [_problem(str(i)) for i in range(25)])
    resp = client.get("/api/v1/problems", params={"page": 1, "page_size": 10})
    body = resp.json()
    assert body["total"] == 25
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert len(body["problems"]) == 10

    resp2 = client.get("/api/v1/problems", params={"page": 3, "page_size": 10})
    assert len(resp2.json()["problems"]) == 5  # last partial page


def test_list_page_beyond_range_returns_empty_not_an_error(tmp_path, monkeypatch):
    _write_fake_corpus(tmp_path, monkeypatch, [_problem(str(i)) for i in range(5)])
    resp = client.get("/api/v1/problems", params={"page": 99, "page_size": 10})
    assert resp.status_code == 200
    assert resp.json()["problems"] == []
    assert resp.json()["total"] == 5


def test_list_filters_by_domain(tmp_path, monkeypatch):
    _write_fake_corpus(
        tmp_path,
        monkeypatch,
        [
            _problem("1", domain=["AI/ML"]),
            _problem("2", domain=["FinTech"]),
            _problem("3", domain=["AI/ML", "Healthcare"]),
        ],
    )
    resp = client.get("/api/v1/problems", params={"domain": "AI/ML"})
    ids = {p["id"] for p in resp.json()["problems"]}
    assert ids == {"1", "3"}


def test_list_filters_by_source(tmp_path, monkeypatch):
    _write_fake_corpus(
        tmp_path, monkeypatch, [_problem("1", source="sih"), _problem("2", source="devpost")]
    )
    resp = client.get("/api/v1/problems", params={"source": "devpost"})
    ids = {p["id"] for p in resp.json()["problems"]}
    assert ids == {"2"}


def test_list_combined_filters_are_ANDed(tmp_path, monkeypatch):
    _write_fake_corpus(
        tmp_path,
        monkeypatch,
        [
            _problem("1", source="sih", domain=["AI/ML"]),
            _problem("2", source="sih", domain=["FinTech"]),
            _problem("3", source="devpost", domain=["AI/ML"]),
        ],
    )
    resp = client.get("/api/v1/problems", params={"source": "sih", "domain": "AI/ML"})
    ids = {p["id"] for p in resp.json()["problems"]}
    assert ids == {"1"}


def test_list_rejects_page_size_above_the_cap(tmp_path, monkeypatch):
    _write_fake_corpus(tmp_path, monkeypatch, [_problem("1")])
    resp = client.get("/api/v1/problems", params={"page_size": 1000})
    assert resp.status_code == 422


def test_list_passes_through_all_nine_enrichment_scores_when_present(tmp_path, monkeypatch):
    """Regression test: BrowseProblem (this response's schema) is a
    separate schema from RankedResult (search's), reading the same
    on-disk fields but kept in sync by hand — it's easy to wire a new
    enrichment field through RankedResult and forget this one, since
    ProblemCard.jsx renders results from both /search and /problems."""
    _write_fake_corpus(
        tmp_path,
        monkeypatch,
        [
            _problem(
                "1",
                novelty_score=8.2,
                dataset_availability_score=4.0,
                hardware_requirement_score=9.0,
                competition_potential_score=6.1,
                social_impact_score=7.0,
                feasibility_score=3.0,
            )
        ],
    )
    resp = client.get("/api/v1/problems")
    problem = resp.json()["problems"][0]
    assert problem["novelty_score"] == 8.2
    assert problem["dataset_availability_score"] == 4.0
    assert problem["hardware_requirement_score"] == 9.0
    assert problem["competition_potential_score"] == 6.1
    assert problem["social_impact_score"] == 7.0
    assert problem["feasibility_score"] == 3.0


def test_random_passes_through_all_nine_enrichment_scores_when_present(tmp_path, monkeypatch):
    _write_fake_corpus(tmp_path, monkeypatch, [_problem("1", novelty_score=8.2, feasibility_score=3.0)])
    resp = client.get("/api/v1/problems/random", params={"count": 1})
    problem = resp.json()["problems"][0]
    assert problem["novelty_score"] == 8.2
    assert problem["feasibility_score"] == 3.0
