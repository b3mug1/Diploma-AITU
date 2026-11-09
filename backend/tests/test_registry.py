"""Registry permissions, history preservation, audit and atomic CSV contracts."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import Assignment, AuditEvent, Locker, Student, User

API = "/api/v1"


def post(client, admin, registry, payload):
    response = client.post(f"{API}/{registry}", headers=admin, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def upload(client, headers, registry, content):
    return client.post(
        f"{API}/{registry}/import",
        headers={**headers, "Content-Type": "text/csv"},
        content=content,
    )


def audits(client, admin):
    response = client.get(API + "/admin/audit-events", headers=admin)
    assert response.status_code == 200
    return [event for event in response.json() if event["entity_type"] in {"student", "locker"}]


def test_edits_preserve_history_account_and_status(client, admin, db_factory):
    student = post(client, admin, "students", {"student_code": "S1", "full_name": "Original"})
    locker = post(client, admin, "lockers", {"locker_number": "A1", "location": "Old"})
    account = post(
        client,
        admin,
        "users",
        {
            "username": "linked",
            "password": "Synthetic-password-123",
            "role": "student",
            "student_id": student["id"],
        },
    )
    ended = post(
        client,
        admin,
        "assignments",
        {
            "student_id": student["id"],
            "locker_id": locker["id"],
        },
    )
    response = client.post(f"{API}/assignments/{ended['id']}/end", headers=admin)
    assert response.status_code == 200
    ended = response.json()
    active = post(
        client,
        admin,
        "assignments",
        {
            "student_id": student["id"],
            "locker_id": locker["id"],
        },
    )
    for registry, record, payload in [
        ("students", student, {"student_code": " S2 ", "full_name": " Renamed "}),
        ("lockers", locker, {"locker_number": " B2 ", "location": None}),
    ]:
        response = client.patch(f"{API}/{registry}/{record['id']}", headers=admin, json=payload)
        assert response.status_code == 200
        assert response.json()["id"] == record["id"]
        assert response.json()["created_at"] == record["created_at"]
    response = client.get(API + "/assignments?active_only=false", headers=admin)
    assert response.json() == [ended, active]
    assert client.get(API + "/lockers", headers=admin).json()[0]["status"] == "occupied"
    with db_factory() as db:
        assert db.get(User, account["id"]).student_id == student["id"]
        assert db.scalar(select(func.count()).select_from(Assignment)) == 2
    logs = audits(client, admin)
    assert len(logs) == 4
    assert logs[0]["before"] == {"locker_number": "A1", "location": "Old", "status": "occupied"}
    assert logs[0]["after"] == {"locker_number": "B2", "location": None, "status": "occupied"}
    assert logs[1]["before"] == {"student_code": "S1", "full_name": "Original"}
    assert logs[1]["after"] == {"student_code": "S2", "full_name": "Renamed"}
    assert all(log["actor_id"] == 1 and log["occurred_at"] for log in logs)
    # Identical edits do not create fictitious changes.
    client.patch(f"{API}/students/{student['id']}", headers=admin, json={"full_name": "Renamed"})
    assert len(audits(client, admin)) == 4


@pytest.mark.parametrize("role", [None, "student", "technician"])
def test_registry_write_and_audit_permissions(client, admin, role):
    headers = {}
    if role:
        student = post(client, admin, "students", {"student_code": "S", "full_name": "Test"})
        payload = {"username": role, "password": "Synthetic-password-123", "role": role}
        if role == "student":
            payload["student_id"] = student["id"]
        post(client, admin, "users", payload)
        token = client.post(
            API + "/auth/login",
            json={
                "username": role,
                "password": payload["password"],
            },
        ).json()["access_token"]
        headers = {"Authorization": "Bearer " + token}
    expected = 403 if role else 401
    for registry, payload, csv in [
        ("students", {"full_name": "Changed"}, "student_code,full_name\nS2,Name\n"),
        ("lockers", {"location": "Changed"}, "locker_number\nA1\n"),
    ]:
        assert (
            client.patch(f"{API}/{registry}/1", headers=headers, json=payload).status_code
            == expected
        )
        assert upload(client, headers, registry, csv).status_code == expected
    assert client.get(API + "/admin/audit-events", headers=headers).status_code == expected


@pytest.mark.parametrize(
    "registry,first,second,field",
    [
        (
            "students",
            {"student_code": "S1", "full_name": "One"},
            {"student_code": "S2", "full_name": "Two"},
            "student_code",
        ),
        ("lockers", {"locker_number": "A1"}, {"locker_number": "A2"}, "locker_number"),
    ],
)
def test_duplicate_update_rolls_back_record_and_audit(
    client, admin, registry, first, second, field
):
    original = post(client, admin, registry, first)
    post(client, admin, registry, second)
    response = client.patch(
        f"{API}/{registry}/{original['id']}", headers=admin, json={field: second[field]}
    )
    assert response.status_code == 409
    assert client.get(f"{API}/{registry}", headers=admin).json()[0] == original
    assert len(audits(client, admin)) == 2
    assert client.patch(f"{API}/{registry}/99999", headers=admin, json=first).status_code == 404


@pytest.mark.parametrize(
    "registry,payload",
    [
        ("students", {}),
        ("students", {"full_name": None}),
        ("students", {"student_code": "   "}),
        ("students", {"id": 9}),
        ("students", {"full_name": "x" * 201}),
        ("students", {"full_name": "a\x00b"}),
        ("lockers", {}),
        ("lockers", {"locker_number": None}),
        ("lockers", {"locker_number": ""}),
        ("lockers", {"status": "available"}),
        ("lockers", {"location": "x" * 201}),
        ("lockers", {"locker_number": "x" * 65}),
    ],
)
def test_invalid_patches(client, admin, registry, payload):
    response = client.patch(f"{API}/{registry}/1", headers=admin, json=payload)
    assert response.status_code == 422
    assert audits(client, admin) == []


@pytest.mark.parametrize(
    "registry,csv,model",
    [
        (
            "students",
            '\ufeffstudent_code,full_name\r\n S1 ,"Test, Student"\r\nS2,Екінші\r\n',
            Student,
        ),
        ("lockers", 'locker_number,location\n A1 ,"Floor 1, east"\nA2,\n', Locker),
        ("lockers", "locker_number\nA1\nA2\n", Locker),
    ],
)
def test_csv_success(client, admin, db_factory, registry, csv, model):
    response = upload(client, admin, registry, csv.encode("utf-8"))
    assert response.status_code == 201, response.text
    assert response.json() == {"created": 2}
    logs = audits(client, admin)
    assert len(logs) == 2
    assert all(log["action"].endswith(".imported") and log["before"] is None for log in logs)
    with db_factory() as db:
        records = list(db.scalars(select(model).order_by(model.id)))
        assert len(records) == 2
        assert {record.id for record in records} == {log["entity_id"] for log in logs}
        if model is Student:
            assert records[0].student_code == "S1"
            assert records[0].full_name == "Test, Student"
        else:
            assert all(record.status == "available" for record in records)
            assert records[1].location is None


@pytest.mark.parametrize(
    "registry,csv,error_row,error_field",
    [
        ("students", "student_code,full_name\nGOOD,Valid\nBAD,   \n", 3, "full_name"),
        ("students", "student_code,full_name\nGOOD,Valid\n GOOD ,Duplicate\n", 3, "student_code"),
        ("lockers", "locker_number,location\nA1,Floor\n A1 ,Other\n", 3, "locker_number"),
        ("students", "student_code,full_name\nGOOD,Valid\nBAD,Name,Extra\n", 3, "row"),
        ("lockers", "locker_number,location\nA1,Floor\nA2\n", 3, "row"),
        ("students", "student_code,full_name\nS1,", 2, "full_name"),
        ("students", "student_code,full_name\nS1,a\x00b\n", 2, "full_name"),
        ("lockers", "locker_number,location\nA1," + "x" * 201 + "\n", 2, "location"),
        ("students", "student_code,full_name\n", 2, "file"),
        ("students", "", 1, "header"),
        ("lockers", "locker_number,locker_number\nA1,A2\n", 1, "header"),
        ("lockers", "locker_number,status\nA1,occupied\n", 1, "header"),
        ("students", "student_code\nS1\n", 1, "header"),
        ("students", 'student_code,full_name\nGOOD,Valid\nBAD,"unclosed', 3, "file"),
        ("students", b"student_code,full_name\nS1,\xff", 1, "file"),
    ],
)
def test_invalid_csv_is_atomic(client, admin, registry, csv, error_row, error_field):
    response = upload(client, admin, registry, csv)
    assert response.status_code == 422, response.text
    assert any(
        error["row"] == error_row and error["field"] == error_field
        for error in response.json()["detail"]["errors"]
    )
    assert client.get(f"{API}/{registry}", headers=admin).json() == []
    assert audits(client, admin) == []


@pytest.mark.parametrize(
    "registry,payload,csv",
    [
        (
            "students",
            {"student_code": "S1", "full_name": "Original"},
            "student_code,full_name\nNEW,Valid\nS1,Overwrite\n",
        ),
        (
            "lockers",
            {"locker_number": "A1", "location": "Original"},
            "locker_number,location\nNEW,Valid\nA1,Overwrite\n",
        ),
    ],
)
def test_import_rejects_existing_identifiers(client, admin, registry, payload, csv):
    original = post(client, admin, registry, payload)
    response = upload(client, admin, registry, csv)
    assert response.status_code == 422
    assert response.json()["detail"]["errors"][0]["row"] == 3
    assert client.get(f"{API}/{registry}", headers=admin).json() == [original]
    assert len(audits(client, admin)) == 1


def test_csv_reports_multiple_errors(client, admin):
    response = upload(
        client, admin, "students", "student_code,full_name\n,\nS1,Valid\nS1,Duplicate\n"
    )
    errors = response.json()["detail"]["errors"]
    assert len(errors) == 3
    assert {error["row"] for error in errors} == {2, 4}


def test_import_limits_and_media_type(client, admin):
    for csv, code in [("x" * (1024 * 1024 + 1), 413), ("locker_number\n" + "A\n" * 1001, 413)]:
        assert upload(client, admin, "lockers", csv).status_code == code
    response = client.post(API + "/lockers/import", headers=admin, json={"data": "A1"})
    assert response.status_code == 415
    assert audits(client, admin) == []


def test_import_late_conflict_rolls_back_all_rows_and_audit(client, admin, monkeypatch, db_factory):
    from app import registry_imports

    original = registry_imports.record_change

    def conflict(db, actor, record, action):
        original(db, actor, record, action)
        if record.student_code == "S2":
            # Emulate a conflict discovered after validation and earlier successful flushes.
            raise IntegrityError("INSERT", {}, Exception("unique constraint"))

    monkeypatch.setattr(registry_imports, "record_change", conflict)
    response = upload(client, admin, "students", "student_code,full_name\nS1,One\nS2,Two\n")
    assert response.status_code == 409
    assert response.json()["detail"]["errors"][0]["row"] == 3
    with db_factory() as db:
        assert db.scalar(select(func.count()).select_from(Student)) == 0
        assert db.scalar(select(func.count()).select_from(AuditEvent)) == 0


def test_status_changes_are_audited(client, admin):
    locker = post(client, admin, "lockers", {"locker_number": "A1"})
    response = client.patch(
        f"{API}/lockers/{locker['id']}/status", headers=admin, json={"status": "maintenance"}
    )
    assert response.status_code == 200
    log = audits(client, admin)[0]
    assert log["action"] == "locker.status_changed"
    assert log["before"]["status"] == "available"
    assert log["after"]["status"] == "maintenance"
    assert (
        client.patch(
            f"{API}/lockers/{locker['id']}/status", headers=admin, json={"status": "occupied"}
        ).status_code
        == 409
    )
    assert len(audits(client, admin)) == 2


def test_openapi_documents_csv_and_patch_contract(client):
    paths = client.get("/openapi.json").json()["paths"]
    for registry, parameter in [("students", "student_id"), ("lockers", "locker_id")]:
        operation = paths[f"{API}/{registry}/import"]["post"]
        assert "text/csv" in operation["requestBody"]["content"]
        assert {"201", "409", "413", "415", "422"}.issubset(operation["responses"])
        assert operation["security"] == [{"HTTPBearer": []}]
        assert "patch" in paths[f"{API}/{registry}/{{{parameter}}}"]
