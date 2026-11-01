"""
Tests for the Resume Value enrichment script (now scoring nine metrics,
not just the original three — see scripts/enrich_resume_value.py's
SCORE_FIELDS/PROMPT_TEMPLATE). Only
app.rag.gemini_client.generate_json() actually calls the network, so
prompt building, response parsing/validation, and enrich()'s
skip-already-scored / write-back logic are all tested without a real
Gemini call.
"""

import json

import pytest

import scripts.enrich_resume_value as enrich_module
from app.rag.gemini_client import GeminiUnavailableError
from scripts.enrich_resume_value import (
    SCORE_FIELDS,
    _build_batch_prompt,
    _parse_batch_response,
    is_fully_scored,
    status_report,
)

PROBLEM_A = {
    "id": "sih:p1",
    "title": "AI Crop Disease Detection",
    "summary": "Detect crop disease from leaf images using computer vision.",
    "domain": ["AI/ML", "Agriculture"],
    "technologies": ["Python", "OpenCV"],
    **{field: None for field in SCORE_FIELDS},
}
PROBLEM_B = {
    "id": "sih:p2",
    "title": "Blockchain Supply Chain Tracker",
    "summary": "Track pharmaceutical supply chains on a blockchain ledger.",
    "domain": ["Blockchain & Web3"],
    "technologies": ["Solidity"],
    **{field: None for field in SCORE_FIELDS},
}


def _full_scores(**overrides) -> dict:
    """A complete, well-formed score entry (all nine fields) — the shape
    _parse_batch_response actually requires per entry. `overrides` lets a
    test set specific fields without retyping all nine each time."""
    scores = {field: 5.0 for field in SCORE_FIELDS}
    scores.update(overrides)
    return scores


def test_build_batch_prompt_includes_every_problem_id_and_title():
    prompt = _build_batch_prompt([PROBLEM_A, PROBLEM_B])
    assert "sih:p1" in prompt
    assert "sih:p2" in prompt
    assert "AI Crop Disease Detection" in prompt
    assert "Blockchain Supply Chain Tracker" in prompt


def test_build_batch_prompt_documents_all_nine_fields():
    prompt = _build_batch_prompt([PROBLEM_A])
    for field in SCORE_FIELDS:
        assert field in prompt


def test_parse_batch_response_accepts_well_formed_scores():
    response = json.dumps(
        [
            {"id": "sih:p1", **_full_scores(resume_value_score=8.5, novelty_score=9.0)},
            {"id": "sih:p2", **_full_scores(resume_value_score=6.0, feasibility_score=3.5)},
        ]
    )
    result = _parse_batch_response(response, {"sih:p1", "sih:p2"})
    assert result["sih:p1"]["resume_value_score"] == 8.5
    assert result["sih:p1"]["novelty_score"] == 9.0
    assert result["sih:p2"]["feasibility_score"] == 3.5


def test_parse_batch_response_ignores_unknown_ids():
    response = json.dumps([{"id": "not-in-this-batch", **_full_scores()}])
    result = _parse_batch_response(response, {"sih:p1"})
    assert result == {}


def test_parse_batch_response_skips_entries_missing_any_score_field():
    # Only resume_value_score present — missing the other eight.
    response = json.dumps([{"id": "sih:p1", "resume_value_score": 8.0}])
    result = _parse_batch_response(response, {"sih:p1"})
    assert result == {}


def test_parse_batch_response_clamps_out_of_range_scores():
    response = json.dumps(
        [{"id": "sih:p1", **_full_scores(resume_value_score=15.0, industry_relevance_score=-3.0)}]
    )
    result = _parse_batch_response(response, {"sih:p1"})
    assert result["sih:p1"]["resume_value_score"] == 10.0
    assert result["sih:p1"]["industry_relevance_score"] == 0.0


def test_parse_batch_response_rejects_invalid_json():
    with pytest.raises(ValueError, match="valid JSON"):
        _parse_batch_response("not json {{{", {"sih:p1"})


def test_parse_batch_response_rejects_non_array():
    with pytest.raises(ValueError, match="JSON array"):
        _parse_batch_response(json.dumps({"id": "sih:p1"}), {"sih:p1"})


def test_enrich_skips_already_scored_problems(tmp_path, monkeypatch):
    already_scored = {**PROBLEM_A, **_full_scores(resume_value_score=9.0)}
    processed_path = tmp_path / "problems.json"
    processed_path.write_text(json.dumps([already_scored]), encoding="utf-8")
    monkeypatch.setattr(enrich_module, "PROCESSED_PATH", processed_path)

    calls = []
    monkeypatch.setattr(enrich_module, "get_gemini_model", lambda: object())
    monkeypatch.setattr(enrich_module, "generate_json", lambda model, prompt, **kwargs: calls.append(prompt) or "[]")

    scored = enrich_module.enrich()

    assert scored == 0
    assert calls == []  # Gemini was never called — nothing needed scoring


def test_is_fully_scored_true_only_when_all_nine_fields_are_set():
    assert is_fully_scored({**PROBLEM_A, **_full_scores()}) is True


def test_is_fully_scored_false_when_any_field_is_missing():
    # The classic pre-regression shape: only the original three fields set.
    partially_scored = {
        **PROBLEM_A,
        "resume_value_score": 8.0,
        "industry_relevance_score": 7.0,
        "technical_depth_score": 9.0,
    }
    assert is_fully_scored(partially_scored) is False


def test_is_fully_scored_false_when_nothing_is_set():
    assert is_fully_scored(PROBLEM_A) is False


def test_enrich_backfills_problems_only_partially_scored_from_before_new_fields_existed(tmp_path, monkeypatch):
    """Regression test: a problem scored before novelty_score etc. were
    added has resume_value_score set but is missing the other six fields.
    enrich() must treat it as needing enrichment, not as already done."""
    partially_scored = {
        **PROBLEM_A,
        "resume_value_score": 8.0,
        "industry_relevance_score": 7.0,
        "technical_depth_score": 9.0,
        # novelty_score and the rest stay None, inherited from PROBLEM_A.
    }
    processed_path = tmp_path / "problems.json"
    processed_path.write_text(json.dumps([partially_scored]), encoding="utf-8")
    monkeypatch.setattr(enrich_module, "PROCESSED_PATH", processed_path)
    monkeypatch.setattr(enrich_module, "get_gemini_model", lambda: object())

    fake_response = json.dumps([{"id": "sih:p1", **_full_scores(novelty_score=6.5)}])
    monkeypatch.setattr(enrich_module, "generate_json", lambda model, prompt, **kwargs: fake_response)

    scored = enrich_module.enrich()

    assert scored == 1
    written = json.loads(processed_path.read_text(encoding="utf-8"))[0]
    for field in SCORE_FIELDS:
        assert written[field] is not None
    assert written["novelty_score"] == 6.5


def test_enrich_one_skips_a_fully_scored_problem(tmp_path, monkeypatch):
    processed_path = tmp_path / "problems.json"
    processed_path.write_text(json.dumps([{**PROBLEM_A, **_full_scores()}]), encoding="utf-8")
    monkeypatch.setattr(enrich_module, "PROCESSED_PATH", processed_path)

    calls = []
    monkeypatch.setattr(enrich_module, "get_gemini_model", lambda: calls.append("called") or object())

    result = enrich_module.enrich_one("sih:p1")

    assert result is False
    assert calls == []  # Gemini was never called


def test_enrich_one_backfills_a_partially_scored_problem(tmp_path, monkeypatch):
    """Same regression as the enrich() test above, but for the lazy
    per-save path: a problem with only the original three fields set must
    still be enriched when re-saved, not skipped as already done."""
    partially_scored = {
        **PROBLEM_A,
        "resume_value_score": 8.0,
        "industry_relevance_score": 7.0,
        "technical_depth_score": 9.0,
    }
    processed_path = tmp_path / "problems.json"
    processed_path.write_text(json.dumps([partially_scored]), encoding="utf-8")
    monkeypatch.setattr(enrich_module, "PROCESSED_PATH", processed_path)
    monkeypatch.setattr(enrich_module, "get_gemini_model", lambda: object())

    fake_response = json.dumps([{"id": "sih:p1", **_full_scores(novelty_score=4.0)}])
    monkeypatch.setattr(enrich_module, "generate_json", lambda model, prompt, **kwargs: fake_response)

    result = enrich_module.enrich_one("sih:p1")

    assert result is True
    written = json.loads(processed_path.read_text(encoding="utf-8"))[0]
    assert written["novelty_score"] == 4.0
    for field in SCORE_FIELDS:
        assert written[field] is not None


def test_enrich_stops_cleanly_on_quota_exhaustion_without_losing_earlier_batches(tmp_path, monkeypatch):
    """Regression test: a Gemini quota/rate-limit error partway through a
    run (GeminiUnavailableError, raised after gemini_client.py's own
    retries give up) must not propagate as an unhandled exception. The
    batch(es) completed before the error stay checkpointed, the batch
    that hit the error is left untouched (still correctly "todo" for the
    next run — never half-written), and enrich() returns normally with
    however many it managed to score."""
    problem_c = {**PROBLEM_A, "id": "sih:p3", "title": "Third Problem"}
    processed_path = tmp_path / "problems.json"
    processed_path.write_text(json.dumps([PROBLEM_A, PROBLEM_B, problem_c]), encoding="utf-8")
    monkeypatch.setattr(enrich_module, "PROCESSED_PATH", processed_path)
    monkeypatch.setattr(enrich_module, "get_gemini_model", lambda: object())

    calls = {"count": 0}

    def fake_generate_json(model, prompt, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return json.dumps([{"id": "sih:p1", **_full_scores(resume_value_score=8.0)}])
        raise GeminiUnavailableError("Gemini call failed after retrying for ~55s: 429 Resource exhausted")

    monkeypatch.setattr(enrich_module, "generate_json", fake_generate_json)

    scored = enrich_module.enrich(batch_size=1)

    assert scored == 1  # only the first batch succeeded before the quota error
    written = {p["id"]: p for p in json.loads(processed_path.read_text(encoding="utf-8"))}
    assert written["sih:p1"]["resume_value_score"] == 8.0  # checkpointed before the error
    assert is_fully_scored(written["sih:p1"]) is True
    # Neither later problem was touched — still correctly "todo", not
    # half-written, so the next run picks them up without re-charging a
    # quota call for sih:p1.
    assert is_fully_scored(written["sih:p2"]) is False
    assert is_fully_scored(written["sih:p3"]) is False
    assert all(written["sih:p2"].get(field) is None for field in SCORE_FIELDS)


def test_status_report_breaks_down_full_partial_and_unscored():
    fully = {**PROBLEM_A, **_full_scores()}
    partially = {**PROBLEM_B, "resume_value_score": 8.0, "industry_relevance_score": 7.0, "technical_depth_score": 9.0}
    unscored = {**PROBLEM_A, "id": "sih:p3"}

    report = status_report([fully, partially, unscored])

    assert report == {"total": 3, "fully_scored": 1, "partially_scored": 1, "unscored": 1}


def test_enrich_scores_a_problem_from_a_brand_new_source_with_no_extra_wiring(tmp_path, monkeypatch):
    """Regression test: enrich() filters purely on is_fully_scored(), with
    no source allow-list anywhere in the path — a problem from a source
    that didn't exist when this script was written (e.g. a newly-added
    scraper) must still enter the same scoring queue automatically."""
    new_source_problem = {**PROBLEM_A, "source": "a_brand_new_scraper_source"}
    processed_path = tmp_path / "problems.json"
    processed_path.write_text(json.dumps([new_source_problem]), encoding="utf-8")
    monkeypatch.setattr(enrich_module, "PROCESSED_PATH", processed_path)
    monkeypatch.setattr(enrich_module, "get_gemini_model", lambda: object())

    fake_response = json.dumps([{"id": "sih:p1", **_full_scores(resume_value_score=7.5)}])
    monkeypatch.setattr(enrich_module, "generate_json", lambda model, prompt, **kwargs: fake_response)

    scored = enrich_module.enrich()

    assert scored == 1
    written = json.loads(processed_path.read_text(encoding="utf-8"))[0]
    assert written["resume_value_score"] == 7.5


def test_enrich_writes_all_nine_scores_back_with_mocked_gemini_call(tmp_path, monkeypatch):
    processed_path = tmp_path / "problems.json"
    processed_path.write_text(json.dumps([PROBLEM_A, PROBLEM_B]), encoding="utf-8")
    monkeypatch.setattr(enrich_module, "PROCESSED_PATH", processed_path)
    monkeypatch.setattr(enrich_module, "get_gemini_model", lambda: object())

    fake_response = json.dumps(
        [
            {"id": "sih:p1", **_full_scores(resume_value_score=8.5, hardware_requirement_score=2.0)},
            {"id": "sih:p2", **_full_scores(resume_value_score=6.0, hardware_requirement_score=9.0)},
        ]
    )
    monkeypatch.setattr(enrich_module, "generate_json", lambda model, prompt, **kwargs: fake_response)

    scored = enrich_module.enrich(batch_size=8)

    assert scored == 2
    written = json.loads(processed_path.read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in written}
    assert by_id["sih:p1"]["resume_value_score"] == 8.5
    assert by_id["sih:p1"]["hardware_requirement_score"] == 2.0
    # Every one of the nine fields actually got written, not just the two asserted above.
    for field in SCORE_FIELDS:
        assert by_id["sih:p2"][field] is not None
