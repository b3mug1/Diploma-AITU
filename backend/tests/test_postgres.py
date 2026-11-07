"""Opt-in integration tests; each fixture creates and removes its own schema."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from tests.test_migrations import migrate

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL for PostgreSQL integration"
)
API = "/api/v1"


def test_postgres_migrations():
    control = create_engine(os.environ["TEST_DATABASE_URL"])
    schema = "migration_" + uuid.uuid4().hex
    with control.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    url = (
        make_url(os.environ["TEST_DATABASE_URL"])
        .update_query_dict({"options": f"-csearch_path={schema}"})
        .render_as_string(hide_password=False)
    )
    try:
        migrate(url, "upgrade", "head")
        migrate(url, "check")
        migrate(url, "downgrade", "base")
        migrate(url, "upgrade", "head")
        migrate(url, "check")
    finally:
        with control.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        control.dispose()


def race(*calls):
    barrier = Barrier(len(calls))

    def run(call):
        barrier.wait(timeout=10)
        return call()

    with ThreadPoolExecutor(max_workers=len(calls)) as executor:
        return list(executor.map(run, calls))


def test_competing_assignments_and_repair(client, admin):
    student = client.post(
        API + "/students",
        headers=admin,
        json={"student_code": "SYNTHETIC", "full_name": "Test Student"},
    ).json()["id"]
    locker = client.post(API + "/lockers", headers=admin, json={"locker_number": "A1"}).json()["id"]

    def assign():
        return client.post(
            API + "/assignments", headers=admin, json={"student_id": student, "locker_id": locker}
        )

    results = race(assign, assign)
    assert sorted(r.status_code for r in results) == [201, 409]
    assignment = next(r.json()["id"] for r in results if r.status_code == 201)
    ended, repair = race(
        lambda: client.post(API + f"/assignments/{assignment}/end", headers=admin),
        lambda: client.post(
            API + "/repairs",
            headers=admin,
            json={"locker_id": locker, "description": "Synthetic fault"},
        ),
    )
    assert ended.status_code == 200
    assert repair.status_code == 201
    assert client.get(API + "/lockers", headers=admin).json()[0]["status"] == "maintenance"
    assert assign().status_code == 409
