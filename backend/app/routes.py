"""Initial API endpoints for the student/locker registry and assignments."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Assignment, Locker, LockerStatus, Role, Student, User
from app.schemas import (
    AssignmentCreate,
    AssignmentRead,
    LockerCreate,
    LockerRead,
    LockerStatusUpdate,
    StudentCreate,
    StudentRead,
)
from app.security import admin_user, current_user

router = APIRouter()


def _commit_or_conflict(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=detail
        ) from exc


@router.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}


@router.post(
    "/students",
    response_model=StudentRead,
    status_code=status.HTTP_201_CREATED,
    tags=["students"],
    dependencies=[Depends(admin_user)],
)
def create_student(payload: StudentCreate, db: Session = Depends(get_db)) -> Student:
    student = Student(**payload.model_dump())
    db.add(student)
    _commit_or_conflict(db, "A student with this code already exists.")
    db.refresh(student)
    return student


@router.get(
    "/students",
    response_model=list[StudentRead],
    tags=["students"],
    dependencies=[Depends(admin_user)],
)
def list_students(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[Student]:
    return list(
        db.scalars(select(Student).order_by(Student.id).offset(offset).limit(limit))
    )


@router.post(
    "/lockers",
    response_model=LockerRead,
    status_code=status.HTTP_201_CREATED,
    tags=["lockers"],
    dependencies=[Depends(admin_user)],
)
def create_locker(payload: LockerCreate, db: Session = Depends(get_db)) -> Locker:
    locker = Locker(**payload.model_dump())
    db.add(locker)
    _commit_or_conflict(db, "A locker with this number already exists.")
    db.refresh(locker)
    return locker


@router.get(
    "/lockers",
    response_model=list[LockerRead],
    tags=["lockers"],
    dependencies=[Depends(admin_user)],
)
def list_lockers(
    locker_status: LockerStatus | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[Locker]:
    statement = select(Locker).order_by(Locker.id)
    if locker_status is not None:
        statement = statement.where(Locker.status == locker_status)
    return list(db.scalars(statement.offset(offset).limit(limit)))


@router.patch(
    "/lockers/{locker_id}/status",
    response_model=LockerRead,
    tags=["lockers"],
    dependencies=[Depends(admin_user)],
)
def update_locker_status(
    locker_id: int,
    payload: LockerStatusUpdate,
    db: Session = Depends(get_db),
) -> Locker:
    locker = db.scalar(
        select(Locker)
        .where(Locker.id == locker_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if locker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Locker not found."
        )
    active_assignment = db.scalar(
        select(Assignment.id).where(
            Assignment.locker_id == locker_id, Assignment.ended_at.is_(None)
        )
    )
    if active_assignment is not None and payload.status != LockerStatus.OCCUPIED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="End the active assignment before changing this locker to a non-occupied status.",
        )
    if payload.status == LockerStatus.OCCUPIED and active_assignment is None:
        raise HTTPException(409, "Create an assignment to occupy a locker.")
    locker.status = payload.status
    _commit_or_conflict(
        db, "The locker status could not be updated due to a data conflict."
    )
    db.refresh(locker)
    return locker


@router.post(
    "/assignments",
    response_model=AssignmentRead,
    status_code=status.HTTP_201_CREATED,
    tags=["assignments"],
    dependencies=[Depends(admin_user)],
)
def create_assignment(
    payload: AssignmentCreate, db: Session = Depends(get_db)
) -> Assignment:
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found."
        )

    locker = db.scalar(
        select(Locker)
        .where(Locker.id == payload.locker_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if locker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Locker not found."
        )
    if locker.status != LockerStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Locker is not available."
        )

    existing = db.scalar(
        select(Assignment.id).where(
            Assignment.locker_id == locker.id,
            Assignment.ended_at.is_(None),
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Locker already has an active assignment.",
        )

    assignment = Assignment(student_id=student.id, locker_id=locker.id)
    locker.status = LockerStatus.OCCUPIED
    db.add(assignment)
    _commit_or_conflict(
        db, "Locker availability changed; refresh the registry and try again."
    )
    db.refresh(assignment)
    return assignment


@router.get("/assignments", response_model=list[AssignmentRead], tags=["assignments"])
def list_assignments(
    active_only: bool = Query(default=True),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[Assignment]:
    statement = select(Assignment).order_by(Assignment.id)
    if user.role == Role.STUDENT:
        statement = statement.where(Assignment.student_id == user.student_id)
    elif user.role != Role.ADMIN:
        raise HTTPException(403, "Assignment access denied.")
    if active_only:
        statement = statement.where(Assignment.ended_at.is_(None))
    return list(db.scalars(statement.offset(offset).limit(limit)))


@router.post(
    "/assignments/{assignment_id}/end",
    response_model=AssignmentRead,
    tags=["assignments"],
    dependencies=[Depends(admin_user)],
)
def end_assignment(assignment_id: int, db: Session = Depends(get_db)) -> Assignment:
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found."
        )
    locker = db.scalar(
        select(Locker)
        .where(Locker.id == assignment.locker_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    db.refresh(assignment)
    if assignment.ended_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Assignment has already ended."
        )

    assignment.ended_at = datetime.now(UTC)
    locker.status = LockerStatus.AVAILABLE
    _commit_or_conflict(db, "The assignment could not be ended due to a data conflict.")
    db.refresh(assignment)
    return assignment
