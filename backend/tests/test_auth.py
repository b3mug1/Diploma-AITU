from datetime import UTC, datetime, timedelta
from sqlalchemy import select
from app.models import AuthSession

API = "/api/v1"


def test_login_logout_and_expiry(client, admin, db_factory):
    assert client.get(API + "/students").status_code == 401
    assert (
        client.post(
            API + "/auth/login", json={"username": "admin", "password": "wrong"}
        ).status_code
        == 401
    )
    assert client.get(API + "/auth/me", headers=admin).json()["role"] == "admin"
    assert client.post(API + "/auth/logout", headers=admin).status_code == 204
    assert client.get(API + "/auth/me", headers=admin).status_code == 401
    login = client.post(
        API + "/auth/login", json={"username": "admin", "password": "Test-password-123"}
    )
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    with db_factory() as db:
        session = db.scalar(select(AuthSession))
        assert session.token_hash != login.json()["access_token"]
        session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert client.get(API + "/auth/me", headers=headers).status_code == 401


def test_accounts_permissions_and_deactivation(client, admin):
    student = client.post(
        API + "/students",
        headers=admin,
        json={"student_code": "S1", "full_name": "Synthetic Student"},
    ).json()
    payload = {
        "username": "student",
        "password": "Test-password-123",
        "role": "student",
        "student_id": student["id"],
    }
    created = client.post(API + "/users", headers=admin, json=payload)
    assert created.status_code == 201
    assert "password_hash" not in created.json()
    assert client.post(API + "/users", headers=admin, json=payload).status_code == 409
    assert (
        client.post(
            API + "/users", headers=admin, json={**payload, "student_id": None}
        ).status_code
        == 422
    )
    login = client.post(
        API + "/auth/login",
        json={"username": "student", "password": payload["password"]},
    ).json()
    headers = {"Authorization": "Bearer " + login["access_token"]}
    assert client.get(API + "/students", headers=headers).status_code == 403
    assert client.post(API + "/users", headers=headers, json=payload).status_code == 403
    assert client.get(API + "/assignments", headers=headers).json() == []
    assert (
        client.post(
            API + f"/users/{created.json()['id']}/deactivate", headers=admin
        ).status_code
        == 200
    )
    assert client.get(API + "/auth/me", headers=headers).status_code == 401
    assert (
        client.post(
            API + "/auth/login",
            json={"username": "student", "password": payload["password"]},
        ).status_code
        == 401
    )


def test_assignment_and_status_guards(client, admin):
    s = client.post(
        API + "/students",
        headers=admin,
        json={"student_code": "S1", "full_name": "Synthetic"},
    ).json()
    locker = client.post(
        API + "/lockers", headers=admin, json={"locker_number": "A1"}
    ).json()
    path = API + f"/lockers/{locker['id']}/status"
    assert (
        client.patch(path, headers=admin, json={"status": "occupied"}).status_code
        == 409
    )
    payload = {"student_id": s["id"], "locker_id": locker["id"]}
    assignment = client.post(API + "/assignments", headers=admin, json=payload)
    assert assignment.status_code == 201
    assert (
        client.post(API + "/assignments", headers=admin, json=payload).status_code
        == 409
    )
    assert (
        client.patch(path, headers=admin, json={"status": "available"}).status_code
        == 409
    )
    end = API + f"/assignments/{assignment.json()['id']}/end"
    assert client.post(end, headers=admin).status_code == 200
    assert client.post(end, headers=admin).status_code == 409
    assert (
        client.post(
            API + "/students",
            headers=admin,
            json={"student_code": "  ", "full_name": "Test"},
        ).status_code
        == 422
    )
