"""
Tests for scripts/backfill_missing_score_fields.py — the one-time
migration for problems that were enriched before
scripts/enrich_resume_value.py scored all nine fields (see that module's
is_fully_scored()). This script deliberately has no prompt/parsing logic
of its own, so these tests only cover its own job: counting
already-full vs. missing problems, calling enrich_resume_value.enrich(),
and reporting accurate before/after numbers — the real enrichment
behavior itself is covered by test_enrich_resume_value.py.
"""

import json

import scripts.backfill_missing_score_fields as backfill_module
import scripts.enrich_resume_value as enrich_module
from scripts.enrich_resume_value import SCORE_FIELDS


def _full_scores(**overrides) -> dict:
    scores = {field: 5.0 for field in SCORE_FIELDS}
    scores.update(overrides)
    return scores


def _write(tmp_path, monkeypatch, problems):
    path = tmp_path / "problems.json"
    path.write_text(json.dumps(problems), encoding="utf-8")
    monkeypatch.setattr(backfill_module, "PROCESSED_PATH", path)
    monkeypatch.setattr(enrich_module, "PROCESSED_PATH", path)
    return path


def test_calls_enrich_and_reports_backfilled_count(tmp_path, monkeypatch):
    partially_scored = {
        "id": "sih:p1",
        "title": "A problem",
        "summary": "s",
        "resume_value_score": 8.0,
        "industry_relevance_score": 7.0,
        "technical_depth_score": 9.0,
    }
    fully_scored = {"id": "sih:p2", "title": "Already done", "summary": "s", **_full_scores()}
    path = _write(tmp_path, monkeypatch, [partially_scored, fully_scored])

    monkeypatch.setattr(enrich_module, "get_gemini_model", lambda: object())
    fake_response = json.dumps([{"id": "sih:p1", **_full_scores(novelty_score=6.0)}])
    monkeypatch.setattr(enrich_module, "generate_json", lambda model, prompt, **kwargs: fake_response)

    backfilled = backfill_module.main()

    assert backfilled == 1
    written = {p["id"]: p for p in json.loads(path.read_text(encoding="utf-8"))}
    for field in SCORE_FIELDS:
        assert written["sih:p1"][field] is not None
    assert written["sih:p1"]["novelty_score"] == 6.0
    # The already-fully-scored problem was never touched/re-requested.
    assert written["sih:p2"] == fully_scored


def test_noop_when_every_problem_already_has_all_nine_fields(tmp_path, monkeypatch):
    fully_scored = {"id": "sih:p1", "title": "Done", "summary": "s", **_full_scores()}
    path = _write(tmp_path, monkeypatch, [fully_scored])

    calls = []
    monkeypatch.setattr(enrich_module, "get_gemini_model", lambda: calls.append("called") or object())

    backfilled = backfill_module.main()

    assert backfilled == 0
    assert calls == []  # enrich() must never even be reached
    assert json.loads(path.read_text(encoding="utf-8")) == [fully_scored]


def test_noop_on_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(backfill_module, "PROCESSED_PATH", tmp_path / "does-not-exist.json")
    assert backfill_module.main() == 0


def test_noop_on_empty_corpus(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, [])
    assert backfill_module.main() == 0


def test_is_idempotent_second_run_is_a_noop_once_everything_is_scored(tmp_path, monkeypatch):
    partially_scored = {
        "id": "sih:p1",
        "title": "A problem",
        "summary": "s",
        "resume_value_score": 8.0,
        "industry_relevance_score": 7.0,
        "technical_depth_score": 9.0,
    }
    path = _write(tmp_path, monkeypatch, [partially_scored])

    monkeypatch.setattr(enrich_module, "get_gemini_model", lambda: object())
    fake_response = json.dumps([{"id": "sih:p1", **_full_scores()}])
    monkeypatch.setattr(enrich_module, "generate_json", lambda model, prompt, **kwargs: fake_response)

    first_run = backfill_module.main()
    assert first_run == 1

    calls = []
    monkeypatch.setattr(enrich_module, "get_gemini_model", lambda: calls.append("called") or object())
    second_run = backfill_module.main()

    assert second_run == 0
    assert calls == []
