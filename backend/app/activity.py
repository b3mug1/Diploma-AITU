"""Transactional audit and in-app notification helpers."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Notification, User, UserRole


def record_event(db: Session, actor: User, action: str, entity_type: str, entity_id: int) -> None:
    db.add(AuditEvent(actor_id=actor.id, actor_username=actor.username,
                      action=action, entity_type=entity_type, entity_id=entity_id))


def notify_student(db: Session, student_id: int, title: str, message: str) -> None:
    recipient = db.scalar(select(User).where(User.student_id == student_id,
                                             User.role == UserRole.STUDENT,
                                             User.is_active.is_(True)))
    if recipient is not None:
        db.add(Notification(user_id=recipient.id, title=title, message=message))


def notify_admins(db: Session, title: str, message: str, exclude_user_id: int) -> None:
    recipients = db.scalars(select(User).where(User.role == UserRole.ADMIN,
                                               User.is_active.is_(True),
                                               User.id != exclude_user_id))
    for recipient in recipients:
        db.add(Notification(user_id=recipient.id, title=title, message=message))
