"""
Tests for scripts/build_corpus.py's score-preservation behavior.

A real incident already happened where rebuilding problems.json from raw
sources silently wiped every already-computed Phase 2 resume-value
enrichment score back to null (those fields don't exist anywhere in
raw/seed data — clean_pipeline() never produces them). These tests lock in
the fix: _restore_resume_value_scores() must copy prior scores onto a
freshly-rebuilt problem with the same id, and main() must call it before
writing, so adding new raw sources (this module's own reason for
existing — SIH historical years, article_ingest.py) never loses them
again.
"""

import json

import scripts.build_corpus as build_corpus
from app.schemas.problem import ProcessedProblem


def _problem(id_, **overrides) -> ProcessedProblem:
    defaults = dict(
        id=id_,
        title="A problem",
        summary="A summary.",
        problem_statement="A problem statement.",
        source="sih",
        domain=[],
        technologies=[],
        skills=[],
    )
    defaults.update(overrides)
    return ProcessedProblem(**defaults)


def test_load_existing_resume_value_scores_reads_only_non_null_fields(tmp_path):
    path = tmp_path / "problems.json"
    path.write_text(
        json.dumps(
            [
                {"id": "sih:p1", "resume_value_score": 8.5, "industry_relevance_score": 7.0, "technical_depth_score": 9.0},
                {"id": "sih:p2", "resume_value_score": None, "industry_relevance_score": None, "technical_depth_score": None},
                {"id": "sih:p3"},  # never had the fields at all
            ]
        ),
        encoding="utf-8",
    )

    scores = build_corpus._load_existing_resume_value_scores(path)

    assert scores == {"sih:p1": {"resume_value_score": 8.5, "industry_relevance_score": 7.0, "technical_depth_score": 9.0}}


def test_load_existing_resume_value_scores_returns_empty_when_no_file_yet(tmp_path):
    assert build_corpus._load_existing_resume_value_scores(tmp_path / "does-not-exist.json") == {}


def test_restore_resume_value_scores_matches_by_id(tmp_path):
    processed = [
        _problem("sih:p1"),  # previously scored
        _problem("sih:p2"),  # never scored
        _problem("article:new"),  # brand new problem from this rebuild
    ]
    existing_scores = {
        "sih:p1": {"resume_value_score": 8.5, "industry_relevance_score": 7.0, "technical_depth_score": 9.0},
    }

    restored = build_corpus._restore_resume_value_scores(processed, existing_scores)

    assert restored == 1
    p1 = next(p for p in processed if p.id == "sih:p1")
    assert p1.resume_value_score == 8.5
    assert p1.industry_relevance_score == 7.0
    assert p1.technical_depth_score == 9.0

    # Untouched — never had a prior score, must not be fabricated one.
    p2 = next(p for p in processed if p.id == "sih:p2")
    assert p2.resume_value_score is None

    new = next(p for p in processed if p.id == "article:new")
    assert new.resume_value_score is None


def test_main_preserves_scores_across_a_full_rebuild_that_adds_new_records(tmp_path, monkeypatch):
    """End-to-end: an existing problems.json with real scores, plus a
    rebuild that adds a brand-new raw source alongside the old one (e.g.
    what SIH historical years / article_ingest.py do) — the pre-existing
    problem's scores must survive, unchanged, in the new file."""
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    out_path = processed_dir / "problems.json"
    out_path.write_text(
        json.dumps(
            [
                {
                    "id": "sih:sih1",
                    "title": "Existing Scored Problem",
                    "summary": "s",
                    "problem_statement": "s",
                    "source": "sih",
                    "domain": [],
                    "technologies": [],
                    "skills": [],
                    "resume_value_score": 8.5,
                    "industry_relevance_score": 7.0,
                    "technical_depth_score": 9.0,
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(build_corpus, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(
        build_corpus,
        "gather_raw_records",
        lambda: [
            # Same source+external_id as the existing problem -> same stable id.
            {"title": "Existing Scored Problem", "description": "s", "source": "sih", "external_id": "sih1"},
            # A brand-new record from an added source, e.g. article_ingest.py.
            {"title": "New Article Problem", "description": "d", "source": "article"},
        ],
    )

    build_corpus.main()

    result = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(result) == 2

    existing = next(p for p in result if p["id"] == "sih:sih1")
    assert existing["resume_value_score"] == 8.5
    assert existing["industry_relevance_score"] == 7.0
    assert existing["technical_depth_score"] == 9.0

    new = next(p for p in result if p["source"] == "article")
    assert new["resume_value_score"] is None  # genuinely new — nothing to restore, nothing fabricated
