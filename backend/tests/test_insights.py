"""Access control and transactional behavior for activity endpoints."""

import os
import uuid

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Role, User
from app.security import hash_password


@pytest.fixture
def client():
    postgres_url = os.getenv("TEST_DATABASE_URL")
    control = None
    schema = "test_" + uuid.uuid4().hex
    if postgres_url:
        control = create_engine(postgres_url)
        with control.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        url = make_url(postgres_url).update_query_dict({"options": f"-csearch_path={schema}"})
        engine = create_engine(url)
    else:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                               poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        if not postgres_url:
            connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        db.add(User(username="admin", password_hash=hash_password("secure-password-123"),
                    role=Role.ADMIN))
        db.commit()

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()
    if control is not None:
        with control.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        control.dispose()


def login(client, username, password):
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_notifications_audit_and_reports_are_scoped(client):
    admin = login(client, "admin", "secure-password-123")
    first = client.post("/api/v1/students", json={"student_code": "S1", "full_name": "One"},
                        headers=admin).json()
    second = client.post("/api/v1/students", json={"student_code": "S2", "full_name": "Two"},
                         headers=admin).json()
    for username, student in (("one", first), ("two", second)):
        response = client.post("/api/v1/users", json={"username": username,
            "password": "secure-password-123", "role": "student", "student_id": student["id"]},
            headers=admin)
        assert response.status_code == 201
    one = login(client, "one", "secure-password-123")
    two = login(client, "two", "secure-password-123")
    assert client.post("/api/v1/lockers", json={"locker_number": "blocked"}).status_code == 401
    assert client.post("/api/v1/lockers", json={"locker_number": "blocked"},
                       headers=one).status_code == 403

    locker = client.post("/api/v1/lockers", json={"locker_number": "A-1", "location": "A"},
                         headers=admin).json()
    assigned = client.post("/api/v1/assignments", json={"student_id": first["id"],
        "locker_id": locker["id"]}, headers=admin)
    assert assigned.status_code == 201
    assert len(client.get("/api/v1/assignments", headers=one).json()) == 1
    assert client.get("/api/v1/assignments", headers=two).json() == []
    notifications = client.get("/api/v1/notifications", headers=one).json()
    assert len(notifications) == 1
    assert client.get("/api/v1/notifications", headers=two).json() == []
    notification_id = notifications[0]["id"]
    assert client.post(f"/api/v1/notifications/{notification_id}/read", headers=two).status_code == 404
    assert client.post(f"/api/v1/notifications/{notification_id}/read", headers=one).json()["read_at"]
    assert client.get("/api/v1/notifications?unread_only=true", headers=one).json() == []

    assert client.get("/api/v1/admin/audit-events", headers=one).status_code == 403
    events = client.get("/api/v1/admin/audit-events", headers=admin).json()
    assert any(event["action"] == "assignment.created" for event in events)
    assert all(event["actor_username"] == "admin" for event in events)
    assert client.get("/api/v1/admin/reports/summary", headers=one).status_code == 403
    report = client.get("/api/v1/admin/reports/summary", headers=admin).json()
    assert report["lockers_total"] == 1
    assert report["assignments_active"] == 1
    assert report["occupancy_rate_percent"] == 100.0
    locations = client.get("/api/v1/admin/reports/locations", headers=admin).json()
    assert locations[0]["by_status"]["occupied"] == 1

    ended = client.post(f"/api/v1/assignments/{assigned.json()['id']}/end", headers=admin)
    assert ended.status_code == 200
    assert len(client.get("/api/v1/notifications?unread_only=true", headers=one).json()) == 1
    assert client.get("/api/v1/admin/reports/summary", headers=admin).json()[
        "assignments_active"] == 0


def test_failed_mutation_does_not_leave_audit_event(client):
    admin = login(client, "admin", "secure-password-123")
    payload = {"locker_number": "A-1"}
    assert client.post("/api/v1/lockers", json=payload, headers=admin).status_code == 201
    assert client.post("/api/v1/lockers", json=payload, headers=admin).status_code == 409
    events = client.get("/api/v1/admin/audit-events?action=locker.created", headers=admin).json()
    assert len(events) == 1
    assert client.get("/api/v1/admin/reports/summary").status_code == 401


def test_deactivation_revokes_student_session(client):
    admin = login(client, "admin", "secure-password-123")
    student = client.post("/api/v1/students", json={"student_code": "S3",
        "full_name": "Three"}, headers=admin).json()
    account = client.post("/api/v1/users", json={"username": "three",
        "password": "secure-password-123", "role": "student", "student_id": student["id"]},
        headers=admin).json()
    student_token = login(client, "three", "secure-password-123")
    assert client.get("/api/v1/notifications", headers=student_token).status_code == 200
    assert client.post(f"/api/v1/users/{account['id']}/deactivate", headers=admin).status_code == 200
    assert client.get("/api/v1/notifications", headers=student_token).status_code == 401
    events = client.get("/api/v1/admin/audit-events?action=user.deactivated", headers=admin).json()
    assert len(events) == 1
