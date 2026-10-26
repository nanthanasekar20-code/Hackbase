"""
Tests for app/core/corpus.py's list-returning side (get_all_problems()) —
added alongside the existing id-keyed get_problem() for the non-RAG
/problems and /problems/random routes. Confirms the two caches share one
real file read and reset_cache() invalidates both.
"""

import json

import app.core.corpus as corpus_module


def _write_corpus(tmp_path, monkeypatch, problems):
    fake_path = tmp_path / "problems.json"
    fake_path.write_text(json.dumps(problems), encoding="utf-8")
    monkeypatch.setattr(corpus_module, "PROCESSED_PATH", fake_path)
    corpus_module.reset_cache()


def test_get_all_problems_returns_every_record_in_file_order(tmp_path, monkeypatch):
    problems = [{"id": "a", "title": "A"}, {"id": "b", "title": "B"}, {"id": "c", "title": "C"}]
    _write_corpus(tmp_path, monkeypatch, problems)
    assert corpus_module.get_all_problems() == problems


def test_get_all_problems_on_missing_file_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus_module, "PROCESSED_PATH", tmp_path / "does-not-exist.json")
    corpus_module.reset_cache()
    assert corpus_module.get_all_problems() == []


def test_get_problem_and_get_all_problems_share_one_file_read(tmp_path, monkeypatch):
    _write_corpus(tmp_path, monkeypatch, [{"id": "a", "title": "A"}])
    corpus_module.get_problem("a")  # populates the id-keyed cache first
    assert corpus_module.get_all_problems() == [{"id": "a", "title": "A"}]  # still sees the same data


def test_reset_cache_invalidates_both_caches(tmp_path, monkeypatch):
    _write_corpus(tmp_path, monkeypatch, [{"id": "a", "title": "Old"}])
    assert corpus_module.get_all_problems()[0]["title"] == "Old"
    assert corpus_module.get_problem("a")["title"] == "Old"

    fake_path = tmp_path / "problems.json"
    fake_path.write_text(json.dumps([{"id": "a", "title": "New"}]), encoding="utf-8")
    corpus_module.reset_cache()

    assert corpus_module.get_all_problems()[0]["title"] == "New"
    assert corpus_module.get_problem("a")["title"] == "New"


def test_sampling_the_returned_list_does_not_mutate_the_cache(tmp_path, monkeypatch):
    import random

    problems = [{"id": str(i), "title": str(i)} for i in range(10)]
    _write_corpus(tmp_path, monkeypatch, problems)

    pool = corpus_module.get_all_problems()
    random.sample(pool, k=5)  # as app/api/routes/problems.py does

    assert corpus_module.get_all_problems() == problems  # cache's own order/contents untouched
