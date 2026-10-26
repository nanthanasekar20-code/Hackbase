"""
Tests for POST /search's optional-personalization wiring
(app/api/routes/search.py). This never requires login — get_optional_user
returns None for an anonymous/invalid-token caller — and only forwards a
logged-in user's interests/skill_level to the Search agent once those are
actually set. The ranking math itself (the boost) is covered by
test_rag_pipeline.py; these tests only check the route decides the right
(interests, skill_level) to pass through, using a real temp-file SQLite
DB + a mocked search_agent.run so no real Chroma index is needed — same
real-db pattern as test_auth.py's favorites tests.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes import search as search_routes
from app.db.session import Base, get_db
from app.main import app

client = TestClient(app)


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def _override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def capture_search_agent(monkeypatch):
    """Replaces the module-level search_agent singleton's run() with a
    spy that records its kwargs and returns an empty candidate list — the
    real Chroma/embedding pipeline is irrelevant to what this route
    decides to pass it."""
    calls = []

    def fake_run(query, top_k=10, interests=None, skill_level=None):
        calls.append({"query": query, "top_k": top_k, "interests": interests, "skill_level": skill_level})
        return []

    monkeypatch.setattr(search_routes.search_agent, "run", fake_run)
    return calls


def _register_and_login(email="alice@example.com"):
    client.post("/api/v1/auth/register", json={"email": email, "password": "correct-horse-battery"})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "correct-horse-battery"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_search_works_anonymously_with_no_personalization(db_session, capture_search_agent):
    resp = client.post("/api/v1/search", json={"query": "ai agriculture"})

    assert resp.status_code == 200
    assert capture_search_agent == [{"query": "ai agriculture", "top_k": 5, "interests": None, "skill_level": None}]


def test_search_passes_none_for_a_logged_in_user_with_no_preferences_set(db_session, capture_search_agent):
    headers = _register_and_login()

    resp = client.post("/api/v1/search", json={"query": "ai agriculture"}, headers=headers)

    assert resp.status_code == 200
    # Identical to the anonymous call above — logging in alone, without
    # ever touching Profile's optional preferences, must not change this.
    assert capture_search_agent == [{"query": "ai agriculture", "top_k": 5, "interests": None, "skill_level": None}]


def test_search_forwards_a_logged_in_users_actual_preferences(db_session, capture_search_agent):
    headers = _register_and_login()
    client.patch(
        "/api/v1/auth/me",
        json={"interests": ["Healthcare", "AI/ML"], "skill_level": "advanced"},
        headers=headers,
    )

    resp = client.post("/api/v1/search", json={"query": "ai agriculture"}, headers=headers)

    assert resp.status_code == 200
    assert capture_search_agent == [
        {
            "query": "ai agriculture",
            "top_k": 5,
            "interests": ["Healthcare", "AI/ML"],
            "skill_level": "advanced",
        }
    ]


def test_search_treats_an_invalid_token_as_anonymous_not_as_an_error(db_session, capture_search_agent):
    resp = client.post(
        "/api/v1/search", json={"query": "ai agriculture"}, headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert resp.status_code == 200
    assert capture_search_agent == [{"query": "ai agriculture", "top_k": 5, "interests": None, "skill_level": None}]


def test_search_requires_no_authentication_header_at_all(db_session, capture_search_agent):
    resp = client.post("/api/v1/search", json={"query": "ai agriculture"})
    assert resp.status_code == 200
