"""
Tests for app/services/live_hackathons_job.py — the scheduled-job wrapper
around scripts/run_live_hackathons.run(). Mocks that function so this
stays fast/offline; its own real behavior is covered by
test_run_live_hackathons.py.
"""

import app.core.live_hackathons as live_hackathons_module
from app.services.live_hackathons_job import run_live_hackathons_refresh


def test_successful_run_resets_the_cache_so_next_read_is_fresh(monkeypatch):
    import scripts.run_live_hackathons as run_live_hackathons_script

    fake_payload = {"updated_at": "now", "count": 1, "per_source_counts": {}, "hackathons": [{"title": "x"}]}
    monkeypatch.setattr(run_live_hackathons_script, "run", lambda: fake_payload)

    reset_calls = []
    monkeypatch.setattr(live_hackathons_module, "reset_cache", lambda: reset_calls.append(True))

    result = run_live_hackathons_refresh()

    assert result == fake_payload
    assert reset_calls == [True]


def test_a_failure_is_caught_and_does_not_raise(monkeypatch):
    import scripts.run_live_hackathons as run_live_hackathons_script

    def _boom():
        raise RuntimeError("scrape pipeline exploded")

    monkeypatch.setattr(run_live_hackathons_script, "run", _boom)

    result = run_live_hackathons_refresh()  # must not raise

    assert result == {"ok": False}
