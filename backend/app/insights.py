"""User notifications, administrator audit history, and aggregate reports."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Assignment, AuditEvent, Locker, LockerStatus, Notification, Student, User
from app.schemas import AdminReport, AuditEventRead, NotificationRead, StatusCount
from app.security import admin_user, current_user

router = APIRouter()


@router.get("/notifications", response_model=list[NotificationRead], tags=["notifications"])
def list_notifications(
    unread_only: bool = False,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    statement = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        statement = statement.where(Notification.read_at.is_(None))
    return list(db.scalars(statement.order_by(Notification.id.desc()).offset(offset).limit(limit)))


@router.post("/notifications/{notification_id}/read", response_model=NotificationRead,
             tags=["notifications"])
def read_notification(notification_id: int, user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    notification = db.scalar(select(Notification).where(Notification.id == notification_id,
                                                        Notification.user_id == user.id))
    if notification is None:
        raise HTTPException(404, "Notification not found.")
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(notification)
    return notification


@router.get("/admin/audit-events", response_model=list[AuditEventRead], tags=["admin"])
def list_audit_events(
    action: str | None = Query(default=None, max_length=64),
    actor_id: int | None = Query(default=None, gt=0),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    statement = select(AuditEvent)
    if action is not None:
        statement = statement.where(AuditEvent.action == action)
    if actor_id is not None:
        statement = statement.where(AuditEvent.actor_id == actor_id)
    return list(db.scalars(statement.order_by(AuditEvent.id.desc()).offset(offset).limit(limit)))


@router.get("/admin/reports/summary", response_model=AdminReport, tags=["admin"])
def report_summary(admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    status_rows = db.execute(select(Locker.status, func.count(Locker.id)).group_by(Locker.status)).all()
    counts = {status: count for status, count in status_rows}
    lockers_total = sum(counts.values())
    active = db.scalar(select(func.count(Assignment.id)).where(Assignment.ended_at.is_(None))) or 0
    total = db.scalar(select(func.count(Assignment.id))) or 0
    students = db.scalar(select(func.count(Student.id))) or 0
    return AdminReport(
        generated_at=datetime.now(UTC),
        lockers_total=lockers_total,
        lockers_by_status=[StatusCount(status=status.value, count=counts.get(status, 0))
                           for status in LockerStatus],
        assignments_active=active,
        assignments_total=total,
        students_total=students,
        occupancy_rate_percent=round(100 * counts.get(LockerStatus.OCCUPIED, 0) / lockers_total, 2)
        if lockers_total else 0.0,
    )


@router.get("/admin/reports/locations", tags=["admin"])
def report_locations(admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Locker.location, Locker.status, func.count(Locker.id))
                      .group_by(Locker.location, Locker.status)
                      .order_by(Locker.location, Locker.status)).all()
    locations = {}
    for location, status, count in rows:
        key = location or "Unspecified"
        entry = locations.setdefault(key, {"location": key, "total": 0,
                                           "by_status": {item.value: 0 for item in LockerStatus}})
        entry["total"] += count
        entry["by_status"][status.value] = count
    return list(locations.values())
