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
from scripts.enrich_resume_value import SCORE_FIELDS, _build_batch_prompt, _parse_batch_response, is_fully_scored

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
