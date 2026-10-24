"""Repair lifecycle; all mutations serialize on the associated locker row."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Assignment, Locker, LockerStatus, RepairRequest, RepairStatus, Role, User
from app.routes import _commit_or_conflict
from app.schemas import RepairAssign, RepairCreate, RepairRead, RepairTransition
from app.security import admin_user, current_user

router = APIRouter(prefix="/repairs", tags=["repairs"])
ACTIVE_REPAIRS = (RepairStatus.OPEN, RepairStatus.ASSIGNED, RepairStatus.IN_PROGRESS)


def lock_locker(db, locker_id):
    locker = db.scalar(
        select(Locker)
        .where(Locker.id == locker_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not locker:
        raise HTTPException(404, "Locker not found.")
    return locker


def visible_repairs(user):
    statement = select(RepairRequest)
    if user.role == Role.STUDENT:
        statement = statement.where(RepairRequest.reporter_id == user.id)
    elif user.role == Role.TECHNICIAN:
        statement = statement.where(RepairRequest.technician_id == user.id)
    return statement


def get_repair(db, repair_id, user):
    repair = db.scalar(visible_repairs(user).where(RepairRequest.id == repair_id))
    if not repair:
        raise HTTPException(404, "Repair request not found.")
    return repair


@router.post("", response_model=RepairRead, status_code=201)
def create_repair(
    payload: RepairCreate, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    if user.role == Role.TECHNICIAN:
        raise HTTPException(403, "Only students and administrators may report faults.")
    locker = lock_locker(db, payload.locker_id)
    if user.role == Role.STUDENT:
        own_assignment = db.scalar(
            select(Assignment.id).where(
                Assignment.student_id == user.student_id,
                Assignment.locker_id == locker.id,
                Assignment.ended_at.is_(None),
            )
        )
        if not own_assignment:
            raise HTTPException(
                403, "You may only report faults for your currently assigned locker."
            )
    if db.scalar(
        select(RepairRequest.id).where(
            RepairRequest.locker_id == locker.id, RepairRequest.status.in_(ACTIVE_REPAIRS)
        )
    ):
        raise HTTPException(409, "Locker already has an active repair request.")
    repair = RepairRequest(
        locker_id=locker.id, reporter_id=user.id, description=payload.description
    )
    # Preserve occupied/out-of-service states; an unassigned available locker is held for repair.
    if locker.status == LockerStatus.AVAILABLE:
        locker.status = LockerStatus.MAINTENANCE
    db.add(repair)
    _commit_or_conflict(db, "An active repair request already exists.")
    db.refresh(repair)
    return repair


@router.get("", response_model=list[RepairRead])
def list_repairs(
    status: RepairStatus | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    statement = visible_repairs(user).order_by(RepairRequest.id)
    if status is not None:
        statement = statement.where(RepairRequest.status == status)
    return list(db.scalars(statement.offset(offset).limit(limit)))


@router.get("/{repair_id}", response_model=RepairRead)
def read_repair(repair_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_repair(db, repair_id, user)


@router.post("/{repair_id}/assign", response_model=RepairRead)
def assign_repair(
    repair_id: int,
    payload: RepairAssign,
    user: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    repair = get_repair(db, repair_id, user)
    lock_locker(db, repair.locker_id)
    db.refresh(repair)
    if repair.status not in (RepairStatus.OPEN, RepairStatus.ASSIGNED):
        raise HTTPException(409, "Only open or assigned requests can be assigned.")
    technician = db.get(User, payload.technician_id)
    if not technician or technician.role != Role.TECHNICIAN or not technician.is_active:
        raise HTTPException(422, "Choose an active technician account.")
    repair.technician_id = technician.id
    repair.status = RepairStatus.ASSIGNED
    db.commit()
    db.refresh(repair)
    return repair


@router.patch("/{repair_id}/status", response_model=RepairRead)
def transition_repair(
    repair_id: int,
    payload: RepairTransition,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    repair = get_repair(db, repair_id, user)
    locker = lock_locker(db, repair.locker_id)
    db.refresh(repair)
    # Recheck ownership after waiting on a concurrent reassignment.
    if user.role == Role.TECHNICIAN and repair.technician_id != user.id:
        raise HTTPException(404, "Repair request not found.")
    if user.role == Role.STUDENT:
        raise HTTPException(403, "Students cannot change repair status.")
    allowed = {
        RepairStatus.OPEN: {RepairStatus.CANCELLED},
        RepairStatus.ASSIGNED: {RepairStatus.IN_PROGRESS, RepairStatus.CANCELLED},
        RepairStatus.IN_PROGRESS: {RepairStatus.RESOLVED, RepairStatus.CANCELLED},
    }
    if payload.status not in allowed.get(repair.status, set()):
        raise HTTPException(409, "Invalid repair status transition.")
    if payload.status == RepairStatus.CANCELLED and user.role != Role.ADMIN:
        raise HTTPException(403, "Only administrators may cancel requests.")
    if payload.status in (RepairStatus.RESOLVED, RepairStatus.CANCELLED):
        if not payload.resolution or not payload.resolution.strip():
            raise HTTPException(422, "A repair outcome or cancellation reason is required.")
        repair.resolution = payload.resolution.strip()
        repair.closed_at = datetime.now(UTC)
        if locker.status == LockerStatus.MAINTENANCE:
            occupied = db.scalar(
                select(Assignment.id).where(
                    Assignment.locker_id == locker.id, Assignment.ended_at.is_(None)
                )
            )
            locker.status = LockerStatus.OCCUPIED if occupied else LockerStatus.AVAILABLE
    repair.status = payload.status
    db.commit()
    db.refresh(repair)
    return repair
