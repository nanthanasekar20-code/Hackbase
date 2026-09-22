"""
Tests for user registration/login/me (app/api/routes/auth.py) and the
favorites feature (app/api/routes/favorites.py). Uses a real temp-file
SQLite database and real bcrypt/JWT — nothing here is mocked, since
password hashing and token round-tripping are exactly the things that
must genuinely work, not just look plausible.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.core.corpus as corpus_module
from app.db.session import Base, get_db
from app.main import app
from app.models.user import User


@pytest.fixture()
def client(tmp_path, monkeypatch):
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

    # A small fake corpus so favorite-hydration tests don't depend on the
    # real 164-problem data/processed/problems.json.
    fake_problems = tmp_path / "problems.json"
    fake_problems.write_text(
        json.dumps([{"id": "sih:p1", "title": "AI Crop Disease Detection", "summary": "...", "domain": ["Agriculture"]}]),
        encoding="utf-8",
    )
    monkeypatch.setattr(corpus_module, "PROCESSED_PATH", fake_problems)
    corpus_module.reset_cache()

    with TestClient(app) as c:
        c.db_engine = engine  # exposed so tests can set up admin users directly (no self-service role change)
        yield c

    app.dependency_overrides.clear()


def _register_and_login(client, email="alice@example.com", password="correct-horse-battery"):
    resp = client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Alice"})
    assert resp.status_code == 201, resp.text
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _promote_to_admin(client, email):
    """Test-only: there's no self-service way to become admin, matching production — see scripts/promote_admin.py."""
    session = sessionmaker(bind=client.db_engine)()
    try:
        user = session.query(User).filter(User.email == email).first()
        user.role = User.ROLE_ADMIN
        session.commit()
    finally:
        session.close()


def test_register_creates_user_and_hides_password(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "password": "supersecret1", "full_name": "Bob"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "bob@example.com"
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_rejects_duplicate_email(client):
    client.post("/api/v1/auth/register", json={"email": "dup@example.com", "password": "supersecret1"})
    resp = client.post("/api/v1/auth/register", json={"email": "dup@example.com", "password": "another-pw-1"})
    assert resp.status_code == 409


def test_login_rejects_wrong_password(client):
    client.post("/api/v1/auth/register", json={"email": "carol@example.com", "password": "the-real-password"})
    resp = client.post("/api/v1/auth/login", json={"email": "carol@example.com", "password": "wrong-password"})
    assert resp.status_code == 401


def test_login_rejects_unknown_email(client):
    resp = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever123"})
    assert resp.status_code == 401


def test_me_requires_authentication(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user_with_valid_token(client):
    headers = _register_and_login(client)
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"


def test_me_rejects_garbage_token(client):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_update_me_changes_full_name_without_password(client):
    headers = _register_and_login(client)
    resp = client.patch("/api/v1/auth/me", json={"full_name": "Alice B."}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Alice B."
    assert resp.json()["email"] == "alice@example.com"  # untouched


def test_update_me_requires_authentication(client):
    resp = client.patch("/api/v1/auth/me", json={"full_name": "Nobody"})
    assert resp.status_code == 401


def test_update_me_rejects_email_change_without_current_password(client):
    headers = _register_and_login(client)
    resp = client.patch("/api/v1/auth/me", json={"email": "new@example.com"}, headers=headers)
    assert resp.status_code == 401


def test_update_me_rejects_email_change_with_wrong_current_password(client):
    headers = _register_and_login(client)
    resp = client.patch(
        "/api/v1/auth/me",
        json={"email": "new@example.com", "current_password": "totally-wrong"},
        headers=headers,
    )
    assert resp.status_code == 401


def test_update_me_changes_email_with_correct_current_password(client):
    headers = _register_and_login(client)
    resp = client.patch(
        "/api/v1/auth/me",
        json={"email": "newalice@example.com", "current_password": "correct-horse-battery"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "newalice@example.com"


def test_update_me_rejects_email_already_taken(client):
    client.post("/api/v1/auth/register", json={"email": "taken@example.com", "password": "supersecret1"})
    headers = _register_and_login(client)
    resp = client.patch(
        "/api/v1/auth/me",
        json={"email": "taken@example.com", "current_password": "correct-horse-battery"},
        headers=headers,
    )
    assert resp.status_code == 409


def test_update_me_changes_password_and_new_password_works_for_login(client):
    headers = _register_and_login(client)
    resp = client.patch(
        "/api/v1/auth/me",
        json={"new_password": "a-brand-new-password1", "current_password": "correct-horse-battery"},
        headers=headers,
    )
    assert resp.status_code == 200

    # old password no longer works
    resp = client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "correct-horse-battery"})
    assert resp.status_code == 401

    # new password does
    resp = client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "a-brand-new-password1"})
    assert resp.status_code == 200


def test_favorites_require_authentication(client):
    resp = client.get("/api/v1/favorites")
    assert resp.status_code == 401
    resp = client.post("/api/v1/favorites", json={"problem_id": "sih:p1"})
    assert resp.status_code == 401


def test_add_and_list_favorite_hydrates_from_corpus(client):
    headers = _register_and_login(client)
    resp = client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "AI Crop Disease Detection"
    assert body["domain"] == ["Agriculture"]
    # New (Favorite-as-project) fields, defaulted on creation.
    assert body["status"] == "saved"
    assert body["plan"] is None
    assert body["task_progress"] == {}

    resp = client.get("/api/v1/favorites", headers=headers)
    assert resp.status_code == 200
    favorites = resp.json()
    assert len(favorites) == 1
    assert favorites[0]["problem_id"] == "sih:p1"


def test_update_favorite_status(client):
    headers = _register_and_login(client)
    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)

    resp = client.patch("/api/v1/favorites/sih:p1", json={"status": "in_progress"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"

    resp = client.get("/api/v1/favorites", headers=headers)
    assert resp.json()[0]["status"] == "in_progress"


def test_update_favorite_plan_and_task_progress(client):
    headers = _register_and_login(client)
    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)

    plan = {"problem_understanding": "...", "roadmap": [{"phase": "MVP", "tasks": ["build it"]}]}
    resp = client.patch("/api/v1/favorites/sih:p1", json={"plan": plan}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["plan"] == plan

    resp = client.patch(
        "/api/v1/favorites/sih:p1", json={"task_progress": {"0-0": True}}, headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["task_progress"] == {"0-0": True}
    assert body["plan"] == plan  # untouched by an update that didn't include it


def test_update_favorite_requires_authentication(client):
    resp = client.patch("/api/v1/favorites/sih:p1", json={"status": "done"})
    assert resp.status_code == 401


def test_update_nonexistent_favorite_returns_404(client):
    headers = _register_and_login(client)
    resp = client.patch("/api/v1/favorites/never-favorited", json={"status": "done"}, headers=headers)
    assert resp.status_code == 404


def test_update_favorite_is_scoped_per_user(client):
    alice_headers = _register_and_login(client, email="alice3@example.com")
    bob_headers = _register_and_login(client, email="bob3@example.com")
    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=alice_headers)

    resp = client.patch("/api/v1/favorites/sih:p1", json={"status": "done"}, headers=bob_headers)
    assert resp.status_code == 404  # bob never favorited it — can't touch alice's


def test_adding_same_favorite_twice_is_idempotent(client):
    headers = _register_and_login(client)
    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)
    resp = client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)
    assert resp.status_code == 201  # still succeeds, doesn't error
    resp = client.get("/api/v1/favorites", headers=headers)
    assert len(resp.json()) == 1  # not duplicated


def test_favoriting_unknown_problem_id_still_saves_with_null_title(client):
    headers = _register_and_login(client)
    resp = client.post("/api/v1/favorites", json={"problem_id": "does-not-exist"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["title"] is None


def test_remove_favorite(client):
    headers = _register_and_login(client)
    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)
    resp = client.delete("/api/v1/favorites/sih:p1", headers=headers)
    assert resp.status_code == 204
    resp = client.get("/api/v1/favorites", headers=headers)
    assert resp.json() == []


def test_favorite_timestamps_are_timezone_aware(client):
    # SQLite doesn't preserve tzinfo, so created_at/updated_at come back
    # naive from the DB even though they're always UTC — the API must
    # attach an explicit offset (see app/schemas/_datetime.py), or a JS
    # client's `new Date(...)` silently misreads it as local time.
    headers = _register_and_login(client)
    resp = client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)
    body = resp.json()
    assert body["created_at"].endswith("Z") or "+" in body["created_at"][10:]
    assert body["updated_at"].endswith("Z") or "+" in body["updated_at"][10:]


def test_user_created_at_is_timezone_aware(client):
    resp = client.post(
        "/api/v1/auth/register", json={"email": "tzcheck@example.com", "password": "supersecret1"}
    )
    created_at = resp.json()["created_at"]
    assert created_at.endswith("Z") or "+" in created_at[10:]


def test_tracking_runs_requires_authentication(client):
    resp = client.get("/api/v1/tracking/runs")
    assert resp.status_code == 401


def test_tracking_runs_rejects_regular_authenticated_user(client):
    headers = _register_and_login(client)
    resp = client.get("/api/v1/tracking/runs", headers=headers)
    assert resp.status_code == 403


def test_tracking_runs_accessible_to_admin(client):
    headers = _register_and_login(client, email="admin@example.com")
    _promote_to_admin(client, "admin@example.com")
    resp = client.get("/api/v1/tracking/runs", headers=headers)
    assert resp.status_code == 200
    assert "experiments" in resp.json()


def test_new_users_default_to_regular_role(client):
    resp = client.post("/api/v1/auth/register", json={"email": "newbie@example.com", "password": "supersecret1"})
    assert resp.json()["role"] == "user"


def test_remove_nonexistent_favorite_returns_404(client):
    headers = _register_and_login(client)
    resp = client.delete("/api/v1/favorites/never-favorited", headers=headers)
    assert resp.status_code == 404


def test_favorites_are_scoped_per_user(client):
    alice_headers = _register_and_login(client, email="alice2@example.com")
    bob_headers = _register_and_login(client, email="bob2@example.com")

    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=alice_headers)

    assert client.get("/api/v1/favorites", headers=alice_headers).json() != []
    assert client.get("/api/v1/favorites", headers=bob_headers).json() == []
