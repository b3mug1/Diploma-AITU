"""Create the first administrator from an interactive terminal."""

import getpass

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User, UserRole
from app.schemas import UserCreate
from app.security import hash_password


def main() -> None:
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.role == UserRole.ADMIN)) is not None:
            raise SystemExit("An administrator already exists.")
        username = input("Administrator username: ").strip()
        password = getpass.getpass("Password (12-128 characters): ")
        if password != getpass.getpass("Repeat password: "):
            raise SystemExit("Passwords do not match.")
        payload = UserCreate(username=username, password=password, role=UserRole.ADMIN)
        db.add(User(username=payload.username.lower(), password_hash=hash_password(password),
                    role=UserRole.ADMIN))
        db.commit()
        print("Administrator created.")


if __name__ == "__main__":
    main()
