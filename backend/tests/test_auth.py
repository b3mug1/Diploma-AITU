from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import AuditEvent, AuthSession

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
        client.post(API + "/users", headers=admin, json={**payload, "student_id": None}).status_code
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
        client.post(API + f"/users/{created.json()['id']}/deactivate", headers=admin).status_code
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


def test_change_own_password_revokes_sessions(client, admin, db_factory):
    payload = {"current_password": "Test-password-123", "new_password": "Replacement-password-456"}
    path = API + "/auth/change-password"
    assert client.post(path, headers=admin, json={**payload, "current_password": "wrong"}).status_code == 400
    assert client.post(path, headers=admin, json={**payload, "new_password": payload["current_password"]}).status_code == 400
    assert client.post(path, headers=admin, json={**payload, "new_password": "short"}).status_code == 422
    assert client.post(path, headers=admin, json=payload).status_code == 204
    assert client.get(API + "/auth/me", headers=admin).status_code == 401
    assert client.post(API + "/auth/login", json={"username": "admin", "password": payload["current_password"]}).status_code == 401
    assert client.post(API + "/auth/login", json={"username": "admin", "password": payload["new_password"]}).status_code == 200
    with db_factory() as db:
        assert db.scalar(select(AuditEvent).where(AuditEvent.action == "user.password_changed"))


def test_admin_reactivation_and_password_reset(client, admin, db_factory):
    created = client.post(API + "/users", headers=admin, json={
        "username": "technician", "password": "Test-password-123", "role": "technician"
    }).json()
    user_id = created["id"]
    login_path = API + "/auth/login"
    old_credentials = {"username": "technician", "password": "Test-password-123"}
    token = client.post(login_path, json=old_credentials).json()["access_token"]
    technician = {"Authorization": "Bearer " + token}
    reset_path = API + f"/users/{user_id}/reset-password"
    assert client.post(reset_path, headers=technician, json={"new_password": "Replacement-password-456"}).status_code == 403
    assert client.post(reset_path, headers=admin, json={"new_password": "short"}).status_code == 422
    assert client.post(reset_path, headers=admin, json={"new_password": "Replacement-password-456"}).status_code == 204
    assert client.get(API + "/auth/me", headers=technician).status_code == 401
    assert client.post(login_path, json=old_credentials).status_code == 401
    new_credentials = {**old_credentials, "password": "Replacement-password-456"}
    assert client.post(login_path, json=new_credentials).status_code == 200
    assert client.post(API + f"/users/{user_id}/deactivate", headers=admin).status_code == 200
    assert client.post(login_path, json=new_credentials).status_code == 401
    assert client.post(API + f"/users/{user_id}/activate", headers=technician).status_code == 401
    assert client.post(API + f"/users/{user_id}/activate", headers=admin).json()["is_active"] is True
    assert client.post(login_path, json=new_credentials).status_code == 200
    with db_factory() as db:
        actions = set(db.scalars(select(AuditEvent.action)).all())
        assert {"user.password_reset", "user.activated"} <= actions


def test_assignment_and_status_guards(client, admin):
    s = client.post(
        API + "/students",
        headers=admin,
        json={"student_code": "S1", "full_name": "Synthetic"},
    ).json()
    locker = client.post(API + "/lockers", headers=admin, json={"locker_number": "A1"}).json()
    path = API + f"/lockers/{locker['id']}/status"
    assert client.patch(path, headers=admin, json={"status": "occupied"}).status_code == 409
    payload = {"student_id": s["id"], "locker_id": locker["id"]}
    assignment = client.post(API + "/assignments", headers=admin, json=payload)
    assert assignment.status_code == 201
    assert client.post(API + "/assignments", headers=admin, json=payload).status_code == 409
    assert client.patch(path, headers=admin, json={"status": "available"}).status_code == 409
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
