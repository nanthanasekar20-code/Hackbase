"""
Tests for the Resume Value enrichment script (Phase 2). Only
app.rag.gemini_client.generate_json() actually calls the network, so
prompt building, response parsing/validation, and enrich()'s
skip-already-scored / write-back logic are all tested without a real
Gemini call.
"""

import json

import pytest

import scripts.enrich_resume_value as enrich_module
from scripts.enrich_resume_value import _build_batch_prompt, _parse_batch_response


PROBLEM_A = {
    "id": "sih:p1",
    "title": "AI Crop Disease Detection",
    "summary": "Detect crop disease from leaf images using computer vision.",
    "domain": ["AI/ML", "Agriculture"],
    "technologies": ["Python", "OpenCV"],
    "resume_value_score": None,
    "industry_relevance_score": None,
    "technical_depth_score": None,
}
PROBLEM_B = {
    "id": "sih:p2",
    "title": "Blockchain Supply Chain Tracker",
    "summary": "Track pharmaceutical supply chains on a blockchain ledger.",
    "domain": ["Blockchain & Web3"],
    "technologies": ["Solidity"],
    "resume_value_score": None,
    "industry_relevance_score": None,
    "technical_depth_score": None,
}


def test_build_batch_prompt_includes_every_problem_id_and_title():
    prompt = _build_batch_prompt([PROBLEM_A, PROBLEM_B])
    assert "sih:p1" in prompt
    assert "sih:p2" in prompt
    assert "AI Crop Disease Detection" in prompt
    assert "Blockchain Supply Chain Tracker" in prompt


def test_parse_batch_response_accepts_well_formed_scores():
    response = json.dumps(
        [
            {"id": "sih:p1", "resume_value_score": 8.5, "industry_relevance_score": 7.0, "technical_depth_score": 9.0},
            {"id": "sih:p2", "resume_value_score": 6.0, "industry_relevance_score": 5.5, "technical_depth_score": 6.5},
        ]
    )
    result = _parse_batch_response(response, {"sih:p1", "sih:p2"})
    assert result["sih:p1"]["resume_value_score"] == 8.5
    assert result["sih:p2"]["technical_depth_score"] == 6.5


def test_parse_batch_response_ignores_unknown_ids():
    response = json.dumps(
        [{"id": "not-in-this-batch", "resume_value_score": 5, "industry_relevance_score": 5, "technical_depth_score": 5}]
    )
    result = _parse_batch_response(response, {"sih:p1"})
    assert result == {}


def test_parse_batch_response_skips_entries_missing_score_fields():
    response = json.dumps([{"id": "sih:p1", "resume_value_score": 8.0}])  # missing 2 fields
    result = _parse_batch_response(response, {"sih:p1"})
    assert result == {}


def test_parse_batch_response_clamps_out_of_range_scores():
    response = json.dumps(
        [{"id": "sih:p1", "resume_value_score": 15.0, "industry_relevance_score": -3.0, "technical_depth_score": 5.0}]
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
    already_scored = {**PROBLEM_A, "resume_value_score": 9.0, "industry_relevance_score": 8.0, "technical_depth_score": 9.0}
    processed_path = tmp_path / "problems.json"
    processed_path.write_text(json.dumps([already_scored]), encoding="utf-8")
    monkeypatch.setattr(enrich_module, "PROCESSED_PATH", processed_path)

    calls = []
    monkeypatch.setattr(enrich_module, "get_gemini_model", lambda: object())
    monkeypatch.setattr(enrich_module, "generate_json", lambda model, prompt, **kwargs: calls.append(prompt) or "[]")

    scored = enrich_module.enrich()

    assert scored == 0
    assert calls == []  # Gemini was never called — nothing needed scoring


def test_enrich_writes_scores_back_with_mocked_gemini_call(tmp_path, monkeypatch):
    processed_path = tmp_path / "problems.json"
    processed_path.write_text(json.dumps([PROBLEM_A, PROBLEM_B]), encoding="utf-8")
    monkeypatch.setattr(enrich_module, "PROCESSED_PATH", processed_path)
    monkeypatch.setattr(enrich_module, "get_gemini_model", lambda: object())

    fake_response = json.dumps(
        [
            {"id": "sih:p1", "resume_value_score": 8.5, "industry_relevance_score": 7.0, "technical_depth_score": 9.0},
            {"id": "sih:p2", "resume_value_score": 6.0, "industry_relevance_score": 5.5, "technical_depth_score": 6.5},
        ]
    )
    monkeypatch.setattr(enrich_module, "generate_json", lambda model, prompt, **kwargs: fake_response)

    scored = enrich_module.enrich(batch_size=8)

    assert scored == 2
    written = json.loads(processed_path.read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in written}
    assert by_id["sih:p1"]["resume_value_score"] == 8.5
    assert by_id["sih:p2"]["technical_depth_score"] == 6.5
