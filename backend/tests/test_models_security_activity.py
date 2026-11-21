import hashlib

import pytest

from app.activity import notify_admins, notify_student, notify_user, record_event
from app.audit import record_change, snapshot
from app.models import AuditEvent, Locker, LockerStatus, LockerType, Notification, Role, Student, User, locker_capacity
from app.security import hash_password, token_digest, verify_password


@pytest.mark.parametrize(
    ("locker_type", "capacity"),
    [
        (LockerType.SMALL_SINGLE_KEY, 1),
        (LockerType.LARGE_SINGLE_PIN, 1),
        (LockerType.MEDIUM_SHARED_KEY, 2),
        (LockerType.MEDIUM_SHARED_PIN, 2),
        (None, 1),
    ],
)
def test_locker_capacity(locker_type, capacity):
    assert locker_capacity(locker_type) == capacity


def test_password_hash_verification_and_token_digest():
    stored = hash_password("Test-password-123")
    assert verify_password("Test-password-123", stored)
    assert not verify_password("Wrong-password", stored)
    assert token_digest("session-token") == hashlib.sha256(b"session-token").hexdigest()


def test_audit_snapshot_and_record_change(db_factory):
    with db_factory() as db:
        admin = db.query(User).filter_by(username="admin").one()
        locker = Locker(locker_number="A-1", location="Block C", locker_type="small_single_key")
        db.add(locker)
        db.flush()

        before = snapshot(locker)
        locker.status = LockerStatus.MAINTENANCE
        record_change(db, admin, locker, "status_update", before)
        db.commit()

        event = db.query(AuditEvent).one()
        assert event.action == "locker.status_changed"
        assert event.before["status"] == LockerStatus.AVAILABLE.value
        assert event.after["status"] == LockerStatus.MAINTENANCE.value


def test_activity_helpers_create_scoped_notifications(db_factory):
    with db_factory() as db:
        student = Student(student_code="ST-1", full_name="Test Student")
        db.add(student)
        db.flush()
        student_user = User(username="student1", password_hash=hash_password("password"), role=Role.STUDENT, student_id=student.id)
        second_admin = User(username="admin2", password_hash=hash_password("password"), role=Role.ADMIN)
        db.add_all([student_user, second_admin])
        db.flush()

        admin = db.query(User).filter_by(username="admin").one()
        record_event(db, admin, "locker.created", "locker", 10)
        notify_student(db, student.id, "Assignment", "Locker assigned")
        notify_user(db, student_user.id, "Repair", "Repair updated")
        notify_admins(db, "Status", "Locker changed", exclude_user_id=admin.id)
        db.commit()

        assert db.query(Notification).count() == 3
