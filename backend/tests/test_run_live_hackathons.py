"""
Tests for scripts/run_live_hackathons.run() — merges every scraper's
output and writes it to disk. Scrapers themselves are replaced with tiny
fakes so this stays fast/offline; each real scraper's own parsing logic
is covered by its own test_live_<source>_scraper.py.
"""

import json

from app.scrapers.base_scraper import BaseScraper
from scripts import run_live_hackathons


class _FakeScraper(BaseScraper):
    def __init__(self, source_name: str, records: list[dict]):
        self.source_name = source_name
        self._records = records

    def fetch(self) -> list[dict]:
        return self._records


class _FailingScraper(BaseScraper):
    source_name = "broken"

    def fetch(self) -> list[dict]:
        raise RuntimeError("site is down")


def test_run_merges_all_scrapers_and_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(run_live_hackathons, "PROCESSED_DIR", tmp_path)
    monkeypatch.setattr(run_live_hackathons, "OUTPUT_PATH", tmp_path / "live_hackathons.json")
    monkeypatch.setattr(
        run_live_hackathons,
        "SCRAPERS",
        [
            _FakeScraper("devpost", [{"title": "A", "source": "devpost", "url": "https://a.example.com"}]),
            _FakeScraper("mlh", [{"title": "B", "source": "mlh", "url": "https://b.example.com"}]),
        ],
    )

    payload = run_live_hackathons.run()

    assert payload["count"] == 2
    assert payload["per_source_counts"] == {"devpost": 1, "mlh": 1}
    assert {h["title"] for h in payload["hackathons"]} == {"A", "B"}
    assert payload["updated_at"] is not None

    written = json.loads((tmp_path / "live_hackathons.json").read_text(encoding="utf-8"))
    assert written == payload


def test_one_failing_scraper_does_not_block_the_others(tmp_path, monkeypatch):
    monkeypatch.setattr(run_live_hackathons, "PROCESSED_DIR", tmp_path)
    monkeypatch.setattr(run_live_hackathons, "OUTPUT_PATH", tmp_path / "live_hackathons.json")
    monkeypatch.setattr(
        run_live_hackathons,
        "SCRAPERS",
        [
            _FailingScraper(),
            _FakeScraper("devpost", [{"title": "Still works", "source": "devpost", "url": "https://x.example.com"}]),
        ],
    )

    payload = run_live_hackathons.run()

    assert payload["count"] == 1
    assert payload["per_source_counts"]["broken"] == 0
    assert payload["hackathons"][0]["title"] == "Still works"


def test_no_real_scrapers_contributing_writes_an_honest_empty_feed(tmp_path, monkeypatch):
    monkeypatch.setattr(run_live_hackathons, "PROCESSED_DIR", tmp_path)
    monkeypatch.setattr(run_live_hackathons, "OUTPUT_PATH", tmp_path / "live_hackathons.json")
    monkeypatch.setattr(run_live_hackathons, "SCRAPERS", [_FakeScraper("devpost", [])])

    payload = run_live_hackathons.run()

    assert payload["count"] == 0
    assert payload["hackathons"] == []
