"""
Small shared reader for the JSON-backed problem corpus
(data/processed/problems.json), used anywhere that needs to look a problem
up by id without going through the vector index (e.g. hydrating a user's
saved favorites with a title/summary). Loaded once per process and cached
in memory — 164 records is nothing to keep resident, and this file only
changes when scripts/build_corpus.py is re-run (a fresh deploy/restart).
"""

from __future__ import annotations

import json
from pathlib import Path

# app/core/corpus.py -> parents[3] = <project_root> (core -> app -> backend -> root),
# matching the same resolution used in app/rag/embeddings.py.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "problems.json"

_cache: dict[str, dict] | None = None


def _load() -> dict[str, dict]:
    global _cache
    if _cache is None:
        if PROCESSED_PATH.exists():
            problems = json.loads(PROCESSED_PATH.read_text(encoding="utf-8"))
            _cache = {p["id"]: p for p in problems if p.get("id")}
        else:
            _cache = {}
    return _cache


def get_problem(problem_id: str) -> dict | None:
    return _load().get(problem_id)


def reset_cache() -> None:
    """Test-only: force the next get_problem() call to re-read the file."""
    global _cache
    _cache = None
