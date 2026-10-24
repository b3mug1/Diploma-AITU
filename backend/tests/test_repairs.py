import pytest

API = "/api/v1"
PASSWORD = "Test-password-123"


def account(client, admin, name, role, student_id=None):
    response = client.post(
        API + "/users",
        headers=admin,
        json={"username": name, "password": PASSWORD, "role": role, "student_id": student_id},
    )
    assert response.status_code == 201, response.text
    login = client.post(API + "/auth/login", json={"username": name, "password": PASSWORD})
    return response.json()["id"], {"Authorization": "Bearer " + login.json()["access_token"]}


@pytest.fixture
def workflow(client, admin):
    s1 = client.post(
        API + "/students", headers=admin, json={"student_code": "S1", "full_name": "Synthetic One"}
    ).json()
    s2 = client.post(
        API + "/students", headers=admin, json={"student_code": "S2", "full_name": "Synthetic Two"}
    ).json()
    _, student = account(client, admin, "student", "student", s1["id"])
    _, other = account(client, admin, "other", "student", s2["id"])
    tech_id, tech = account(client, admin, "tech", "technician")
    _, other_tech = account(client, admin, "other-tech", "technician")
    locker = client.post(API + "/lockers", headers=admin, json={"locker_number": "A1"}).json()["id"]
    assignment = client.post(
        API + "/assignments", headers=admin, json={"student_id": s1["id"], "locker_id": locker}
    ).json()["id"]
    return student, other, tech_id, tech, other_tech, locker, assignment


def test_repair_lifecycle_and_visibility(client, admin, workflow):
    student, other, tech_id, tech, other_tech, locker, assignment = workflow
    payload = {"locker_id": locker, "description": "Synthetic broken hinge"}
    assert client.post(API + "/repairs", headers=other, json=payload).status_code == 403
    assert client.post(API + "/repairs", headers=tech, json=payload).status_code == 403
    created = client.post(API + "/repairs", headers=student, json=payload)
    assert created.status_code == 201, created.text
    path = API + f"/repairs/{created.json()['id']}"
    assert client.post(API + "/repairs", headers=student, json=payload).status_code == 409
    assert client.get(path, headers=other).status_code == 404
    assert client.get(path, headers=tech).status_code == 404
    assert client.get(API + "/repairs", headers=other).json() == []
    assert (
        client.patch(path + "/status", headers=student, json={"status": "cancelled"}).status_code
        == 403
    )
    assert (
        client.post(path + "/assign", headers=admin, json={"technician_id": 999}).status_code == 422
    )
    assert (
        client.post(path + "/assign", headers=admin, json={"technician_id": tech_id}).status_code
        == 200
    )
    assert client.get(path, headers=other_tech).status_code == 404
    assert client.get(path, headers=tech).status_code == 200
    assert (
        client.patch(
            path + "/status", headers=tech, json={"status": "resolved", "resolution": "done"}
        ).status_code
        == 409
    )
    assert (
        client.patch(path + "/status", headers=tech, json={"status": "in_progress"}).status_code
        == 200
    )
    assert (
        client.post(path + "/assign", headers=admin, json={"technician_id": tech_id}).status_code
        == 409
    )
    assert client.post(API + f"/assignments/{assignment}/end", headers=admin).status_code == 200
    status_path = API + f"/lockers/{locker}/status"
    assert client.patch(status_path, headers=admin, json={"status": "available"}).status_code == 409
    assert (
        client.patch(path + "/status", headers=tech, json={"status": "resolved"}).status_code == 422
    )
    closed = client.patch(
        path + "/status", headers=tech, json={"status": "resolved", "resolution": "Hinge replaced"}
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["closed_at"] and closed.json()["resolution"] == "Hinge replaced"
    assert client.get(API + "/lockers", headers=admin).json()[0]["status"] == "available"
    assert (
        client.patch(
            path + "/status", headers=admin, json={"status": "cancelled", "resolution": "test"}
        ).status_code
        == 409
    )


def test_cancellation_preserves_occupied_and_out_of_service(client, admin, workflow):
    student, _, _, _, _, locker, _ = workflow
    created = client.post(
        API + "/repairs",
        headers=student,
        json={"locker_id": locker, "description": "Synthetic fault"},
    ).json()
    path = API + f"/repairs/{created['id']}/status"
    assert (
        client.patch(
            path, headers=admin, json={"status": "cancelled", "resolution": "Duplicate report"}
        ).status_code
        == 200
    )
    assert client.get(API + "/lockers", headers=admin).json()[0]["status"] == "occupied"
    free = client.post(API + "/lockers", headers=admin, json={"locker_number": "B1"}).json()["id"]
    client.patch(API + f"/lockers/{free}/status", headers=admin, json={"status": "out_of_service"})
    repair = client.post(
        API + "/repairs", headers=admin, json={"locker_id": free, "description": "Synthetic fault"}
    ).json()
    client.patch(
        API + f"/repairs/{repair['id']}/status",
        headers=admin,
        json={"status": "cancelled", "resolution": "Keep disabled"},
    )
    assert client.get(API + "/lockers", headers=admin).json()[1]["status"] == "out_of_service"


def test_student_assignments_are_scoped(client, admin, workflow):
    student, other, _, tech, _, _, _ = workflow
    assert len(client.get(API + "/assignments", headers=student).json()) == 1
    assert client.get(API + "/assignments", headers=other).json() == []
    assert client.get(API + "/assignments", headers=tech).status_code == 403
