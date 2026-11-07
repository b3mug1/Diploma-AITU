"""Account login and administrator-managed user creation."""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.activity import record_event
from app.database import get_db
from app.models import AuthSession, Student, User
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
DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


@router.post("/auth/login", response_model=TokenRead)
def login(payload: Login, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username.lower()))
    valid = verify_password(payload.password, user.password_hash if user else DUMMY_HASH)
    if not valid or not user or not user.is_active:
        raise HTTPException(401, "Invalid credentials.", headers={"WWW-Authenticate": "Bearer"})
    now = datetime.now(UTC)
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
    token = secrets.token_urlsafe(32)
    expires_at = now + timedelta(hours=8)
    db.add(AuthSession(token_hash=token_digest(token), user_id=user.id, expires_at=expires_at))
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return TokenRead(access_token=token, expires_at=expires_at)


@router.post("/auth/logout", status_code=204)
def logout(user: User = Depends(current_user), credentials=Depends(bearer),
           db: Session = Depends(get_db)):
    db.execute(delete(AuthSession).where(AuthSession.token_hash == token_digest(credentials.credentials)))
    db.commit()


@router.get("/auth/me", response_model=UserRead)
def me(user: User = Depends(current_user)):
    return user


@router.post("/users", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, admin: User = Depends(admin_user),
                db: Session = Depends(get_db)):
    if payload.student_id is not None and db.get(Student, payload.student_id) is None:
        raise HTTPException(404, "Student not found.")
    user = User(username=payload.username.lower(), password_hash=hash_password(payload.password),
                role=payload.role, student_id=payload.student_id)
    db.add(user)
    try:
        db.flush()
        record_event(db, admin, "user.created", "user", user.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Username or student account already exists.") from exc
    db.refresh(user)
    return user


@router.post("/users/{user_id}/deactivate", response_model=UserRead)
def deactivate_user(user_id: int, admin: User = Depends(admin_user),
                    db: Session = Depends(get_db)):
    if admin.id == user_id:
        raise HTTPException(409, "Cannot deactivate your own administrator account.")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found.")
    if user.is_active:
        user.is_active = False
        db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
        record_event(db, admin, "user.deactivated", "user", user_id)
        db.commit()
    return user
