"""Create or reset the admin user."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.db.session import create_all_tables, SessionLocal
from backend.app.db.models import User
from backend.app.security import hash_password


def main() -> None:
    create_all_tables()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "admin@parkpulse.io").first()
        if user:
            user.hashed_password = hash_password("Admin@123")
            user.role = "admin"
            db.commit()
            print("Admin password reset: admin@parkpulse.io / Admin@123")
        else:
            user = User(
                email="admin@parkpulse.io",
                hashed_password=hash_password("Admin@123"),
                full_name="Admin User",
                phone="9999999999",
                role="admin",
            )
            db.add(user)
            db.commit()
            print("Admin created: admin@parkpulse.io / Admin@123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
