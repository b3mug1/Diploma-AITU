"""Create the first administrator interactively or via environment variables after running migrations."""

import getpass
import os

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Role, User
from app.schemas import UserCreate
from app.security import hash_password


def main():
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.role == Role.ADMIN, User.is_active.is_(True))):
            raise SystemExit("An administrator already exists; use the authenticated /users API.")
        username = (os.getenv("ADMIN_USERNAME") or input("Administrator username: ")).strip()
        password = os.getenv("ADMIN_PASSWORD") or getpass.getpass("Password (12–128 characters): ")
        if not os.getenv("ADMIN_PASSWORD") and password != getpass.getpass("Repeat password: "):
            raise SystemExit("Passwords do not match.")
        payload = UserCreate(username=username, password=password, role=Role.ADMIN)
        db.add(
            User(
                username=payload.username.lower(),
                password_hash=hash_password(password),
                role=Role.ADMIN,
            )
        )
        db.commit()
        print("Administrator created.")


if __name__ == "__main__":
    main()
