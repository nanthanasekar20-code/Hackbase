from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    ROLE_USER = "user"
    ROLE_ADMIN = "admin"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    # "user" (default) | "admin" — see app.api.deps.require_admin. No
    # signup flow lets someone pick their own role; promoting an account
    # to admin is a deliberate one-off (scripts/promote_admin.py).
    role = Column(String, nullable=False, server_default=ROLE_USER)
    # --- Optional personalization (Profile page) — entirely opt-in. Both
    # are null for every account by default, including every pre-existing
    # one, and are used only as a ranking BOOST in app/rag/retriever.py,
    # never a filter: a user who never sets these sees identical search
    # results to today. ---
    # Domain/category tags, reusing app.core.taxonomy.DOMAINS verbatim
    # (same list the problem corpus itself is tagged with). Stored as JSON
    # same as Favorite.plan/task_progress — SQLite has no native array
    # column type.
    interests = Column(JSON, nullable=True)
    # Reuses app.core.taxonomy.SKILL_LEVELS — see that constant's docstring
    # for why this is a defined-now, conventional vocabulary rather than
    # one scraped from real problem data (no problem is actually tagged
    # with a difficulty yet).
    skill_level = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
