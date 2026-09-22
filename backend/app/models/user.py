from sqlalchemy import Column, DateTime, Integer, String
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
