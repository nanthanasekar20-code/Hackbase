"""
Tests for scripts/promote_admin.py — the one-off used to make an account
admin, since there's no signup flow or API endpoint that lets someone pick
their own role. Runs the real script function against a real temp-file
SQLite DB (monkeypatching SessionLocal so it doesn't touch the real
configured database), not a reimplementation of its logic.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.session import Base
from app.models.user import User
from scripts import promote_admin

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture()
def db_session_factory(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'promote_test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(bind=engine)
    monkeypatch.setattr(promote_admin, "SessionLocal", TestSessionLocal)
    return TestSessionLocal


def _create_user(session_factory, email, role=User.ROLE_USER):
    db = session_factory()
    try:
        user = User(email=email, hashed_password=hash_password("whatever123"), role=role)
        db.add(user)
        db.commit()
    finally:
        db.close()


def test_promote_makes_regular_user_admin(db_session_factory, capsys):
    _create_user(db_session_factory, "toadmin@example.com")

    promote_admin.promote("toadmin@example.com")

    db = db_session_factory()
    user = db.query(User).filter(User.email == "toadmin@example.com").first()
    db.close()
    assert user.role == User.ROLE_ADMIN
    assert "now an admin" in capsys.readouterr().out


def test_promote_is_idempotent_for_already_admin_user(db_session_factory, capsys):
    _create_user(db_session_factory, "already@example.com", role=User.ROLE_ADMIN)

    promote_admin.promote("already@example.com")  # must not error

    assert "already an admin" in capsys.readouterr().out


def test_promote_unknown_email_exits_with_clear_error(db_session_factory):
    with pytest.raises(SystemExit, match="No account found"):
        promote_admin.promote("nobody@example.com")


def test_promote_admin_works_as_a_real_standalone_subprocess(tmp_path):
    """
    Regression: an earlier version of this script raised
    "InvalidRequestError: ... failed to locate a name ('Favorite')" when
    actually run as `python -m scripts.promote_admin <email>` — because
    nothing had imported app.models.favorite yet, so SQLAlchemy couldn't
    resolve User.favorites' string-based relationship. The same-process
    tests above didn't catch this: pytest had already imported the full
    app (and therefore Favorite) via other test modules first, masking
    the bug. This runs the actual command in a fresh process, the way a
    person promoting themselves to admin actually would.
    """
    db_path = tmp_path / "subprocess_test.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path}"}

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR, env=env, check=True, capture_output=True, text=True,
    )

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO users (email, hashed_password, role) VALUES (?, ?, ?)",
        ("subprocess-test@example.com", "irrelevant-hash", "user"),
    )
    conn.commit()
    conn.close()

    result = subprocess.run(
        [sys.executable, "-m", "scripts.promote_admin", "subprocess-test@example.com"],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "now an admin" in result.stdout

    conn = sqlite3.connect(db_path)
    role = conn.execute("SELECT role FROM users WHERE email = ?", ("subprocess-test@example.com",)).fetchone()[0]
    conn.close()
    assert role == "admin"
