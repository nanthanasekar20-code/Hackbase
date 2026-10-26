"""
Small shared reader for the JSON-backed problem corpus
(data/processed/problems.json), used anywhere that needs to look a problem
up by id without going through the vector index (e.g. hydrating a user's
saved favorites with a title/summary), or — see get_all_problems() below —
needs the whole corpus as a plain list rather than a single lookup (the
non-RAG /problems and /problems/random endpoints in
app/api/routes/problems.py: a random sample and a flat paginated browse
are just reads over this same list, no vector search involved). Loaded
once per process and cached in memory — 600-ish records is nothing to
keep resident, and this file only changes when scripts/build_corpus.py is
re-run (a fresh deploy/restart).
"""

from __future__ import annotations

import json
from pathlib import Path

# app/core/corpus.py -> parents[3] = <project_root> (core -> app -> backend -> root),
# matching the same resolution used in app/rag/embeddings.py.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "problems.json"

# _list_cache is the one real read of the file; _cache (id -> record) is
# derived from it rather than re-parsing the JSON a second time.
_list_cache: list[dict] | None = None
_cache: dict[str, dict] | None = None


def _load_list() -> list[dict]:
    global _list_cache
    if _list_cache is None:
        _list_cache = json.loads(PROCESSED_PATH.read_text(encoding="utf-8")) if PROCESSED_PATH.exists() else []
    return _list_cache


def _load() -> dict[str, dict]:
    global _cache
    if _cache is None:
        _cache = {p["id"]: p for p in _load_list() if p.get("id")}
    return _cache


def get_problem(problem_id: str) -> dict | None:
    return _load().get(problem_id)


def get_all_problems() -> list[dict]:
    """The full corpus, in file order, as a plain list — for callers that
    need to sample/filter/paginate across everything rather than look up
    one id. Returns the same cached list object every call; callers that
    reorder it (e.g. random.sample) get a new list back from that call
    and don't mutate this one."""
    return _load_list()


def reset_cache() -> None:
    """Test-only: force the next get_problem()/get_all_problems() call to re-read the file."""
    global _cache, _list_cache
    _cache = None
    _list_cache = None
