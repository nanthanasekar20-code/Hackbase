"""
Tests for scripts/correct_backfill_first_seen_dates.py — the one-time
correction for scripts/backfill_first_seen.py's placeholder-date side
effect (every pre-existing problem falsely reading as "New" for
NEW_BADGE_DAYS after the backfill ran). Covers: finding the backfill date
from the data (not a hardcoded guess), only touching problems stamped
with exactly that date, and the idempotency guarantee (a second run is a
no-op once the correction has already happened).
"""

import json
from datetime import datetime, timedelta, timezone

import scripts.correct_backfill_first_seen_dates as correct_module

TODAY = datetime.now(timezone.utc).date()


def _iso(days_ago: int) -> str:
    return (TODAY - timedelta(days=days_ago)).isoformat()


def _write(tmp_path, monkeypatch, problems):
    path = tmp_path / "problems.json"
    path.write_text(json.dumps(problems), encoding="utf-8")
    monkeypatch.setattr(correct_module, "PROCESSED_PATH", path)
    return path


def test_corrects_the_dominant_recent_date_and_leaves_others_untouched(tmp_path, monkeypatch):
    # 5 problems backfilled "today" (the artifact), 1 genuinely newer, 1 genuinely older.
    problems = (
        [{"id": f"sih:p{i}", "first_seen_at": _iso(0)} for i in range(5)]
        + [{"id": "article:new", "first_seen_at": _iso(1)}]
        + [{"id": "sih:genuinely-old", "first_seen_at": _iso(40)}]
    )
    path = _write(tmp_path, monkeypatch, problems)

    touched = correct_module.main()

    assert touched == 5
    result = {p["id"]: p["first_seen_at"] for p in json.loads(path.read_text(encoding="utf-8"))}
    # The 5 backfilled ones moved to ~30 days ago, well outside the 7-day New window.
    for i in range(5):
        corrected = datetime.fromisoformat(result[f"sih:p{i}"]).date()
        assert (TODAY - corrected).days == correct_module.CORRECTED_AGE_DAYS
    # Genuinely different dates are untouched.
    assert result["article:new"] == _iso(1)
    assert result["sih:genuinely-old"] == _iso(40)


def test_is_idempotent_second_run_is_a_noop(tmp_path, monkeypatch):
    problems = [{"id": f"sih:p{i}", "first_seen_at": _iso(0)} for i in range(5)]
    path = _write(tmp_path, monkeypatch, problems)

    first_run = correct_module.main()
    assert first_run == 5
    after_first = json.loads(path.read_text(encoding="utf-8"))

    second_run = correct_module.main()
    assert second_run == 0
    after_second = json.loads(path.read_text(encoding="utf-8"))
    assert after_first == after_second  # file genuinely unchanged by the second run


def test_does_not_misfire_when_no_date_has_a_majority(tmp_path, monkeypatch):
    """A spread of genuinely-different recent dates (ordinary day-to-day
    scraping, not a bulk backfill stamp) must be left alone."""
    problems = [
        {"id": "a", "first_seen_at": _iso(0)},
        {"id": "b", "first_seen_at": _iso(1)},
        {"id": "c", "first_seen_at": _iso(2)},
        {"id": "d", "first_seen_at": _iso(3)},
    ]
    path = _write(tmp_path, monkeypatch, problems)

    touched = correct_module.main()

    assert touched == 0
    assert json.loads(path.read_text(encoding="utf-8")) == problems


def test_noop_when_dominant_date_is_already_old(tmp_path, monkeypatch):
    """Simulates the state right after a correction has already run (or
    the corpus was just never affected) — nothing inside the New-badge
    window, so there's nothing to fix."""
    problems = [{"id": f"sih:p{i}", "first_seen_at": _iso(40)} for i in range(5)]
    _write(tmp_path, monkeypatch, problems)

    assert correct_module.main() == 0


def test_noop_on_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(correct_module, "PROCESSED_PATH", tmp_path / "does-not-exist.json")
    assert correct_module.main() == 0


def test_noop_on_empty_corpus(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, [])
    assert correct_module.main() == 0


def test_noop_when_no_problem_has_first_seen_at(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, [{"id": "a"}, {"id": "b"}])
    assert correct_module.main() == 0
