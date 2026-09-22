"""
One-off: promotes an existing account to admin (role="admin"), gating
access to internal pages like /tracking. There's no signup flow that lets
someone pick their own role — this is the intended way to create the
first (or any) admin.

Run as: python -m scripts.promote_admin <email>
"""

from __future__ import annotations

import argparse

from app.db.session import SessionLocal

# app.models.favorite must be imported before any query touches User:
# User.favorites is a string-based relationship("Favorite", ...), which
# SQLAlchemy only resolves against classes that have actually been
# imported somewhere. The full app (app.main) imports it transitively via
# the favorites route, but this script doesn't otherwise touch it — without
# this line, db.query(User) fails with "failed to locate a name
# ('Favorite')" when run standalone (python -m scripts.promote_admin).
import app.models.favorite  # noqa: F401
from app.models.user import User


def promote(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise SystemExit(f"No account found with email {email!r}.")
        if user.role == User.ROLE_ADMIN:
            print(f"{email} is already an admin — nothing to do.")
            return
        user.role = User.ROLE_ADMIN
        db.commit()
        print(f"{email} is now an admin.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email", help="Email of the account to promote to admin")
    args = parser.parse_args()
    promote(args.email)
