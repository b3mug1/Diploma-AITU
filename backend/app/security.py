"""Password hashing and revocable, database-backed bearer sessions."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuthSession, Role, User

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return salt + ":" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    salt, expected = stored.split(":")
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return hmac.compare_digest(digest.hex(), expected)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    session = db.get(AuthSession, token_digest(credentials.credentials)) if credentials else None
    expires_at = session.expires_at if session else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if session and expires_at > datetime.now(UTC):
        user = db.get(User, session.user_id)
        if user and user.is_active:
            return user
    raise HTTPException(
        401,
        "Authentication required or session expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(403, "Administrator access required.")
    return user
