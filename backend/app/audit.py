"""Transactional audit helpers; registry snapshots contain no account secrets."""

from app.activity import record_event
from app.models import Locker


def snapshot(record):
    fields = (
        ("locker_number", "location", "status")
        if isinstance(record, Locker)
        else ("student_code", "full_name")
    )
    return {field: getattr(record, field) for field in fields}


def record_change(db, actor, record, action, before=None):
    entity = "locker" if isinstance(record, Locker) else "student"
    verb = {
        "create": "created",
        "update": "updated",
        "status_update": "status_changed",
        "import": "imported",
    }[action]
    record_event(
        db, actor, f"{entity}.{verb}", entity, record.id, before=before, after=snapshot(record)
    )
