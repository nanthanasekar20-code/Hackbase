"""
Unit tests for KaggleScraper (problem-statement corpus). Mirrors
test_live_kaggle_scraper.py's approach: fetch() must degrade gracefully
to [] with no credentials configured, and parse()'s mapping logic is
tested against fixture objects shaped like kaggle's own ApiCompetition,
never the real network.
"""

from app.core.config import settings
from app.scrapers.kaggle_scraper import KaggleScraper


class FakeCompetition:
    """Stand-in for kaggle's ApiCompetition — same attributes KaggleScraper.parse() reads."""

    def __init__(self, title="", description="", organization_name="", category="", ref="", url=""):
        self.title = title
        self.description = description
        self.organization_name = organization_name
        self.category = category
        self.ref = ref
        self.url = url


def test_fetch_returns_empty_list_when_credentials_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "kaggle_username", "")
    monkeypatch.setattr(settings, "kaggle_key", "")
    assert KaggleScraper().fetch() == []
    assert KaggleScraper().run_safe() == []


def test_parses_title_description_and_metadata():
    comp = FakeCompetition(
        title="Titanic Redux",
        description="Predict survival on a fictional retelling of the Titanic dataset.",
        organization_name="Kaggle",
        category="Playground",
        ref="titanic-redux",
        url="https://www.kaggle.com/c/titanic-redux",
    )

    records = KaggleScraper().parse([comp])

    assert len(records) == 1
    record = records[0]
    assert record["title"] == "Titanic Redux"
    assert record["description"] == comp.description
    assert record["organization"] == "Kaggle"
    assert record["source"] == "kaggle"
    assert record["hackathon_name"] == "Titanic Redux"
    assert record["external_id"] == "kaggle:titanic-redux"
    assert record["category"] == "Playground"
    assert record["url"] == "https://www.kaggle.com/c/titanic-redux"


def test_skips_entries_with_no_description():
    comp = FakeCompetition(title="No Description Comp", description="", ref="x")
    assert KaggleScraper().parse([comp]) == []


def test_skips_entries_with_no_title():
    comp = FakeCompetition(title="", description="Has a description but no title.", ref="x")
    assert KaggleScraper().parse([comp]) == []


def test_empty_list_returns_empty_list():
    assert KaggleScraper().parse([]) == []
