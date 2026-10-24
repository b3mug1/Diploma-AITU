"""Authentication and administrator-managed accounts (no public registration)."""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import SESSION_HOURS
from app.database import get_db
from app.models import AuthSession, Student, User
from app.routes import _commit_or_conflict
from app.schemas import Login, TokenRead, UserCreate, UserRead
from app.security import (
    admin_user,
    bearer,
    current_user,
    hash_password,
    token_digest,
    verify_password,
)

router = APIRouter(tags=["auth"])
# Equal-cost verification for unknown accounts, without storing a real password.
DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


@router.post("/auth/login", response_model=TokenRead)
def login(payload: Login, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username.lower()))
    valid = verify_password(
        payload.password, user.password_hash if user else DUMMY_HASH
    )
    if not valid or not user or not user.is_active:
        raise HTTPException(
            401, "Invalid credentials.", headers={"WWW-Authenticate": "Bearer"}
        )
    now = datetime.now(UTC)
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
    token = secrets.token_urlsafe(32)
    expires_at = now + timedelta(hours=SESSION_HOURS)
    db.add(
        AuthSession(
            token_hash=token_digest(token), user_id=user.id, expires_at=expires_at
        )
    )
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return TokenRead(access_token=token, expires_at=expires_at)


@router.post("/auth/logout", status_code=204)
def logout(
    user: User = Depends(current_user),
    credentials=Depends(bearer),
    db: Session = Depends(get_db),
):
    db.execute(
        delete(AuthSession).where(
            AuthSession.token_hash == token_digest(credentials.credentials)
        )
    )
    db.commit()


@router.get("/auth/me", response_model=UserRead)
def me(user: User = Depends(current_user)):
    return user


@router.post(
    "/users",
    response_model=UserRead,
    status_code=201,
    dependencies=[Depends(admin_user)],
)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if payload.student_id is not None and not db.get(Student, payload.student_id):
        raise HTTPException(404, "Student not found.")
    user = User(
        username=payload.username.lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        student_id=payload.student_id,
    )
    db.add(user)
    _commit_or_conflict(db, "Username or student account already exists.")
    db.refresh(user)
    return user


@router.get("/users", response_model=list[UserRead], dependencies=[Depends(admin_user)])
def users(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list(db.scalars(select(User).order_by(User.id).offset(offset).limit(limit)))


@router.post("/users/{user_id}/deactivate", response_model=UserRead)
def deactivate(
    user_id: int, admin: User = Depends(admin_user), db: Session = Depends(get_db)
):
    if admin.id == user_id:
        raise HTTPException(409, "Cannot deactivate your own administrator account.")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found.")
    user.is_active = False
    db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
    db.commit()
    return user
