from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Favorite(Base):
    """
    A user's saved hackathon problem — this is HackBase's "My Projects"
    workspace entry (Phase: real accounts), not just a bookmark: it also
    carries the generated roadmap plan and per-task checklist progress, so
    a user's whole in-progress project follows their login rather than
    living in one browser's localStorage.

    problem_id references the string id from data/processed/problems.json
    (e.g. "sih:p1") — problems live in the JSON-backed corpus/Chroma index,
    not in this database, so this is a plain string reference rather than a
    foreign key.
    """

    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "problem_id", name="uq_user_problem"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    problem_id = Column(String, nullable=False, index=True)
    # "saved" | "in_progress" | "done" — mirrors the frontend's STATUS enum
    # (frontend/src/hooks/useProjects.js); enforced there, not with a DB
    # CHECK constraint, to keep adding a status simple on both sides.
    status = Column(String, nullable=False, server_default="saved")
    # The Planning Agent's generated roadmap for this problem (see
    # PlanResponse), stored verbatim so it doesn't need regenerating on
    # every visit. Null until the user has generated one.
    plan = Column(JSON, nullable=True)
    # {"<stage_index>-<task_index>": true} checklist state for the plan
    # above.
    task_progress = Column(JSON, nullable=True)
    # Generated once (lazily, on first GET .../export-pptx) and cached here
    # so re-downloading the same roadmap's PPT never needs regenerating it
    # or re-uploading a plan payload — see app/api/routes/favorites.py.
    # Null until the first export. Cleared (set back to null) whenever the
    # plan changes, since a stale PPT for an old roadmap would be wrong.
    pptx_file = Column(LargeBinary, nullable=True)
    pptx_filename = Column(String, nullable=True)
    # Same idea, but a .pdf rendering of the same plan (see
    # app/services/pdf_builder.py) — used by "View PPT" to open directly
    # in the browser's own PDF viewer, since browsers can't render .pptx.
    pdf_file = Column(LargeBinary, nullable=True)
    pdf_filename = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="favorites")
