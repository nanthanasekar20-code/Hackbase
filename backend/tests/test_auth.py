"""
Tests for user registration/login/me (app/api/routes/auth.py) and the
favorites feature (app/api/routes/favorites.py). Uses a real temp-file
SQLite database and real bcrypt/JWT — nothing here is mocked, since
password hashing and token round-tripping are exactly the things that
must genuinely work, not just look plausible.
"""

import io
import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from pptx import Presentation
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.core.corpus as corpus_module
from app.api.routes import auth as auth_routes
from app.core.config import settings
from app.core.email import EmailNotConfiguredError
from app.core.security import PASSWORD_RESET_PURPOSE
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


# --- Optional personalization (interests/skill_level) on PATCH /auth/me
# — entirely opt-in; see UserUpdate's docstring for the []/"" clear
# sentinels and app/rag/retriever.py for where these actually get used.


def test_new_user_has_no_personalization_set(client):
    headers = _register_and_login(client)
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.json()["interests"] == []
    assert resp.json()["skill_level"] is None


def test_update_me_sets_interests_and_skill_level(client):
    headers = _register_and_login(client)
    resp = client.patch(
        "/api/v1/auth/me",
        json={"interests": ["Healthcare", "AI/ML"], "skill_level": "advanced"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["interests"] == ["Healthcare", "AI/ML"]
    assert resp.json()["skill_level"] == "advanced"


def test_update_me_requires_no_current_password_for_personalization(client):
    """Unlike email/password, these aren't login credentials — no reason
    to gate them behind current_password."""
    headers = _register_and_login(client)
    resp = client.patch("/api/v1/auth/me", json={"interests": ["FinTech"]}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["interests"] == ["FinTech"]


def test_update_me_rejects_an_interest_outside_the_taxonomy(client):
    headers = _register_and_login(client)
    resp = client.patch("/api/v1/auth/me", json={"interests": ["Not A Real Domain"]}, headers=headers)
    assert resp.status_code == 422


def test_update_me_rejects_a_skill_level_outside_the_vocabulary(client):
    headers = _register_and_login(client)
    resp = client.patch("/api/v1/auth/me", json={"skill_level": "expert"}, headers=headers)
    assert resp.status_code == 422


def test_update_me_omitting_personalization_leaves_it_unchanged(client):
    headers = _register_and_login(client)
    client.patch("/api/v1/auth/me", json={"interests": ["FinTech"], "skill_level": "advanced"}, headers=headers)

    resp = client.patch("/api/v1/auth/me", json={"full_name": "Alice B."}, headers=headers)

    assert resp.json()["interests"] == ["FinTech"]
    assert resp.json()["skill_level"] == "advanced"


def test_update_me_clears_interests_with_an_empty_list(client):
    headers = _register_and_login(client)
    client.patch("/api/v1/auth/me", json={"interests": ["FinTech"]}, headers=headers)

    resp = client.patch("/api/v1/auth/me", json={"interests": []}, headers=headers)

    assert resp.json()["interests"] == []


def test_update_me_clears_skill_level_with_an_empty_string(client):
    headers = _register_and_login(client)
    client.patch("/api/v1/auth/me", json={"skill_level": "advanced"}, headers=headers)

    resp = client.patch("/api/v1/auth/me", json={"skill_level": ""}, headers=headers)

    assert resp.json()["skill_level"] is None


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


def _set_corpus(tmp_path, monkeypatch, problems):
    path = tmp_path / "problems_override.json"
    path.write_text(json.dumps(problems), encoding="utf-8")
    monkeypatch.setattr(corpus_module, "PROCESSED_PATH", path)
    corpus_module.reset_cache()


def test_add_favorite_triggers_background_enrichment_when_problem_is_unscored(client, tmp_path, monkeypatch):
    _set_corpus(tmp_path, monkeypatch, [{"id": "sih:p1", "title": "A problem", "summary": "s", "domain": []}])

    import scripts.enrich_resume_value as enrich_module

    calls = []
    monkeypatch.setattr(enrich_module, "enrich_one", lambda problem_id: calls.append(problem_id) or False)

    headers = _register_and_login(client)
    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)

    assert calls == ["sih:p1"]


def test_add_favorite_skips_background_enrichment_when_problem_is_fully_scored(client, tmp_path, monkeypatch):
    from scripts.enrich_resume_value import SCORE_FIELDS

    _set_corpus(
        tmp_path,
        monkeypatch,
        [
            {
                "id": "sih:p1",
                "title": "A problem",
                "summary": "s",
                "domain": [],
                **{field: 5.0 for field in SCORE_FIELDS},
            }
        ],
    )

    import scripts.enrich_resume_value as enrich_module

    calls = []
    monkeypatch.setattr(enrich_module, "enrich_one", lambda problem_id: calls.append(problem_id) or False)

    headers = _register_and_login(client)
    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)

    assert calls == []


def test_add_favorite_triggers_background_enrichment_when_problem_is_only_partially_scored(client, tmp_path, monkeypatch):
    """Regression test for the bug Fix 2 targets: a problem scored before
    the six newer score fields existed has resume_value_score set but is
    missing the rest — (re-)saving it must still trigger enrichment,
    instead of the old "resume_value_score is None" check wrongly
    treating it as permanently done."""
    _set_corpus(
        tmp_path,
        monkeypatch,
        [
            {
                "id": "sih:p1",
                "title": "A problem",
                "summary": "s",
                "domain": [],
                "resume_value_score": 8.0,
                "industry_relevance_score": 7.0,
                "technical_depth_score": 9.0,
            }
        ],
    )

    import scripts.enrich_resume_value as enrich_module

    calls = []
    monkeypatch.setattr(enrich_module, "enrich_one", lambda problem_id: calls.append(problem_id) or False)

    headers = _register_and_login(client)
    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)

    assert calls == ["sih:p1"]


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


# --- verify-password (Profile page's gate before showing new-password fields) ---


def test_verify_password_requires_authentication(client):
    resp = client.post("/api/v1/auth/verify-password", json={"current_password": "whatever"})
    assert resp.status_code == 401


def test_verify_password_accepts_correct_password(client):
    headers = _register_and_login(client)
    resp = client.post(
        "/api/v1/auth/verify-password", json={"current_password": "correct-horse-battery"}, headers=headers
    )
    assert resp.status_code == 200


def test_verify_password_rejects_wrong_password(client):
    headers = _register_and_login(client)
    resp = client.post("/api/v1/auth/verify-password", json={"current_password": "nope"}, headers=headers)
    assert resp.status_code == 401


# --- forgot-password / reset-password ---


def test_forgot_password_unknown_email_returns_generic_message_without_sending(client, monkeypatch):
    calls = []
    monkeypatch.setattr(auth_routes, "send_email", lambda **kw: calls.append(kw))

    resp = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert resp.status_code == 200
    assert "reset link has been sent" in resp.json()["message"]
    assert calls == []  # never attempted — nothing to email


def test_forgot_password_known_email_sends_email_with_reset_link(client, monkeypatch):
    calls = []
    monkeypatch.setattr(auth_routes, "send_email", lambda **kw: calls.append(kw))
    _register_and_login(client, email="dana@example.com")

    resp = client.post("/api/v1/auth/forgot-password", json={"email": "dana@example.com"})
    assert resp.status_code == 200
    assert "reset link has been sent" in resp.json()["message"]
    assert len(calls) == 1
    assert calls[0]["to"] == "dana@example.com"
    assert "reset-password?token=" in calls[0]["body"]


def test_forgot_password_returns_503_when_email_not_configured_for_known_user(client, monkeypatch):
    def _raise(**kw):
        raise EmailNotConfiguredError("Email sending is not configured on this server.")

    monkeypatch.setattr(auth_routes, "send_email", _raise)
    _register_and_login(client, email="erin@example.com")

    resp = client.post("/api/v1/auth/forgot-password", json={"email": "erin@example.com"})
    assert resp.status_code == 503


def test_reset_password_with_valid_token_changes_password_and_logs_in(client, monkeypatch):
    captured = {}
    monkeypatch.setattr(auth_routes, "send_email", lambda **kw: captured.update(kw))
    _register_and_login(client, email="frank@example.com")
    client.post("/api/v1/auth/forgot-password", json={"email": "frank@example.com"})

    token = captured["body"].split("token=")[1].split("\n")[0].strip()
    resp = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "brand-new-pw-1"})
    assert resp.status_code == 200

    # old password no longer works, new one does
    resp = client.post("/api/v1/auth/login", json={"email": "frank@example.com", "password": "correct-horse-battery"})
    assert resp.status_code == 401
    resp = client.post("/api/v1/auth/login", json={"email": "frank@example.com", "password": "brand-new-pw-1"})
    assert resp.status_code == 200


def test_reset_password_rejects_garbage_token(client):
    resp = client.post("/api/v1/auth/reset-password", json={"token": "not-a-real-token", "new_password": "whatever1"})
    assert resp.status_code == 400


def test_reset_password_rejects_expired_token(client):
    _register_and_login(client, email="grace@example.com")
    expired = jwt.encode(
        {
            "sub": "grace@example.com",
            "purpose": PASSWORD_RESET_PURPOSE,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    resp = client.post("/api/v1/auth/reset-password", json={"token": expired, "new_password": "whatever1"})
    assert resp.status_code == 400


def test_reset_password_rejects_a_normal_access_token(client):
    """An ordinary login session token has no `purpose` claim — it must not double as a reset token."""
    headers = _register_and_login(client, email="henry@example.com")
    access_token = headers["Authorization"].split(" ")[1]
    resp = client.post(
        "/api/v1/auth/reset-password", json={"token": access_token, "new_password": "whatever1"}
    )
    assert resp.status_code == 400


# --- GET /favorites/{problem_id}/export-pptx — cached-on-the-row PPT export ---

MINIMAL_PLAN = {
    "problem_understanding": "Farmers need to detect crop disease early from photos.",
    "tech_stack": ["Python", "TensorFlow"],
    "architecture": "A mobile app uploads photos to an API running a CNN classifier.",
    "roadmap": [{"phase": "MVP", "tasks": ["Train baseline model"], "milestones": []}],
    "deliverables": ["Working demo"],
    "resources": [],
}


def test_export_pptx_requires_authentication(client):
    resp = client.get("/api/v1/favorites/sih:p1/export-pptx")
    assert resp.status_code == 401


def test_export_pptx_404_when_not_favorited(client):
    headers = _register_and_login(client)
    resp = client.get("/api/v1/favorites/sih:p1/export-pptx", headers=headers)
    assert resp.status_code == 404


def test_export_pptx_404_when_favorited_but_no_plan_yet(client):
    headers = _register_and_login(client)
    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)
    resp = client.get("/api/v1/favorites/sih:p1/export-pptx", headers=headers)
    assert resp.status_code == 404


def test_export_pptx_generates_a_valid_presentation_and_marks_has_pptx(client):
    headers = _register_and_login(client)
    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)
    client.patch("/api/v1/favorites/sih:p1", json={"plan": MINIMAL_PLAN}, headers=headers)

    # Not yet generated — the save above doesn't eagerly build one.
    favorites = client.get("/api/v1/favorites", headers=headers).json()
    assert favorites[0]["has_pptx"] is False

    resp = client.get("/api/v1/favorites/sih:p1/export-pptx", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    prs = Presentation(io.BytesIO(resp.content))
    assert len(prs.slides) > 0

    favorites = client.get("/api/v1/favorites", headers=headers).json()
    assert favorites[0]["has_pptx"] is True


def test_export_pptx_second_call_reuses_the_cached_copy(client):
    headers = _register_and_login(client)
    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)
    client.patch("/api/v1/favorites/sih:p1", json={"plan": MINIMAL_PLAN}, headers=headers)

    first = client.get("/api/v1/favorites/sih:p1/export-pptx", headers=headers)
    second = client.get("/api/v1/favorites/sih:p1/export-pptx", headers=headers)
    assert first.content == second.content  # byte-identical — the second call served the cached copy


def test_saving_a_new_plan_invalidates_the_cached_pptx(client):
    headers = _register_and_login(client)
    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)
    client.patch("/api/v1/favorites/sih:p1", json={"plan": MINIMAL_PLAN}, headers=headers)
    client.get("/api/v1/favorites/sih:p1/export-pptx", headers=headers)

    favorites = client.get("/api/v1/favorites", headers=headers).json()
    assert favorites[0]["has_pptx"] is True

    regenerated_plan = {**MINIMAL_PLAN, "problem_understanding": "A regenerated roadmap."}
    client.patch("/api/v1/favorites/sih:p1", json={"plan": regenerated_plan}, headers=headers)

    favorites = client.get("/api/v1/favorites", headers=headers).json()
    assert favorites[0]["has_pptx"] is False  # cleared — stale PPT for the old plan must not be served

    # Still works — regenerates lazily for the new plan.
    resp = client.get("/api/v1/favorites/sih:p1/export-pptx", headers=headers)
    assert resp.status_code == 200


# --- GET /favorites/{problem_id}/view-pdf — "View PPT" in-browser ---


def test_view_pdf_requires_authentication(client):
    resp = client.get("/api/v1/favorites/sih:p1/view-pdf")
    assert resp.status_code == 401


def test_view_pdf_404_when_not_favorited(client):
    headers = _register_and_login(client)
    resp = client.get("/api/v1/favorites/sih:p1/view-pdf", headers=headers)
    assert resp.status_code == 404


def test_view_pdf_404_when_favorited_but_no_plan_yet(client):
    headers = _register_and_login(client)
    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)
    resp = client.get("/api/v1/favorites/sih:p1/view-pdf", headers=headers)
    assert resp.status_code == 404


def test_view_pdf_generates_a_real_pdf_inline_and_marks_has_pdf(client):
    headers = _register_and_login(client)
    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)
    client.patch("/api/v1/favorites/sih:p1", json={"plan": MINIMAL_PLAN}, headers=headers)

    favorites = client.get("/api/v1/favorites", headers=headers).json()
    assert favorites[0]["has_pdf"] is False

    resp = client.get("/api/v1/favorites/sih:p1/view-pdf", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    # inline, not attachment — opens in the browser's own viewer rather than downloading
    assert resp.headers["content-disposition"].startswith("inline")
    assert resp.content[:4] == b"%PDF"

    favorites = client.get("/api/v1/favorites", headers=headers).json()
    assert favorites[0]["has_pdf"] is True


def test_view_pdf_second_call_reuses_the_cached_copy(client):
    headers = _register_and_login(client)
    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)
    client.patch("/api/v1/favorites/sih:p1", json={"plan": MINIMAL_PLAN}, headers=headers)

    first = client.get("/api/v1/favorites/sih:p1/view-pdf", headers=headers)
    second = client.get("/api/v1/favorites/sih:p1/view-pdf", headers=headers)
    assert first.content == second.content


def test_saving_a_new_plan_invalidates_the_cached_pdf_too(client):
    headers = _register_and_login(client)
    client.post("/api/v1/favorites", json={"problem_id": "sih:p1"}, headers=headers)
    client.patch("/api/v1/favorites/sih:p1", json={"plan": MINIMAL_PLAN}, headers=headers)
    client.get("/api/v1/favorites/sih:p1/view-pdf", headers=headers)

    regenerated_plan = {**MINIMAL_PLAN, "problem_understanding": "A regenerated roadmap."}
    client.patch("/api/v1/favorites/sih:p1", json={"plan": regenerated_plan}, headers=headers)

    favorites = client.get("/api/v1/favorites", headers=headers).json()
    assert favorites[0]["has_pdf"] is False

    resp = client.get("/api/v1/favorites/sih:p1/view-pdf", headers=headers)
    assert resp.status_code == 200
