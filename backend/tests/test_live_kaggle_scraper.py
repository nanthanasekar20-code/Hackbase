"""
Unit tests for LiveKaggleScraper. Two things to cover, neither touching
the network: (1) fetch() degrades gracefully to [] when KAGGLE_USERNAME/
KAGGLE_KEY aren't configured, same as every other credential-gated
feature in this app; (2) parse()'s mapping logic against fixture objects
shaped like the kaggle package's own ApiCompetition (title/url/deadline).
"""

from datetime import datetime, timezone

from app.core.config import settings
from app.scrapers.live_kaggle_scraper import LiveKaggleScraper


class FakeCompetition:
    """Stand-in for kaggle's ApiCompetition — same attributes LiveKaggleScraper.parse() reads."""

    def __init__(self, title="", url="", deadline=None):
        self.title = title
        self.url = url
        self.deadline = deadline


def test_fetch_returns_empty_list_when_credentials_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "kaggle_username", "")
    monkeypatch.setattr(settings, "kaggle_key", "")
    assert LiveKaggleScraper().fetch() == []
    assert LiveKaggleScraper().run_safe() == []


def test_fetch_returns_empty_list_when_only_username_configured(monkeypatch):
    monkeypatch.setattr(settings, "kaggle_username", "someone")
    monkeypatch.setattr(settings, "kaggle_key", "")
    assert LiveKaggleScraper().fetch() == []


def test_parses_title_url_and_deadline():
    deadline = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    competitions = [FakeCompetition(title="Titanic Redux", url="https://kaggle.com/c/titanic-redux", deadline=deadline)]

    records = LiveKaggleScraper().parse(competitions)

    assert len(records) == 1
    assert records[0]["title"] == "Titanic Redux"
    assert records[0]["url"] == "https://kaggle.com/c/titanic-redux"
    assert records[0]["source"] == "kaggle"
    assert records[0]["deadline"] == deadline.isoformat()


def test_handles_missing_deadline():
    competitions = [FakeCompetition(title="Getting Started", url="https://kaggle.com/c/getting-started", deadline=None)]
    records = LiveKaggleScraper().parse(competitions)
    assert records[0]["deadline"] is None


def test_skips_entries_with_no_url():
    competitions = [FakeCompetition(title="Missing URL", url="")]
    records = LiveKaggleScraper().parse(competitions)
    assert records == []


def test_skips_entries_with_no_title():
    competitions = [FakeCompetition(title="", url="https://kaggle.com/c/no-title")]
    records = LiveKaggleScraper().parse(competitions)
    assert records == []


def test_empty_list_returns_empty_list():
    assert LiveKaggleScraper().parse([]) == []
