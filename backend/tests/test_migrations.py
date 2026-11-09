"""Exercise versioned upgrades, legacy adoption, downgrade and schema parity."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parents[1]


def migrate(url, *args):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT,
        env={**os.environ, "DATABASE_URL": url},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("legacy", [False, True])
def test_upgrade_downgrade_and_legacy_data(tmp_path, legacy):
    url = "sqlite:///" + str(tmp_path / "migration.db")
    migrate(url, "upgrade", "0001")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO students (student_code, full_name) VALUES ('SYNTHETIC', 'Test Student')"
            )
        )
        connection.execute(
            text("INSERT INTO lockers (locker_number) VALUES ('LEGACY1'), ('LEGACY2')")
        )
        connection.execute(
            text(
                "INSERT INTO assignments (student_id, locker_id, ended_at) "
                "VALUES (1, 1, CURRENT_TIMESTAMP), (1, 2, NULL)"
            )
        )
        if legacy:
            connection.execute(text("DROP TABLE alembic_version"))
    if legacy:
        migrate(url, "stamp", "0001")
    migrate(url, "upgrade", "head")
    migrate(url, "check")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT full_name FROM students")) == "Test Student"
        assert connection.scalar(text("SELECT COUNT(*) FROM assignments")) == 2
        assert (
            connection.scalar(text("SELECT COUNT(*) FROM assignments WHERE ended_at IS NULL")) == 1
        )
        assert connection.scalar(text("SELECT COUNT(*) FROM lockers")) == 2
    assert "repair_requests" in inspect(engine).get_table_names()
    assert "audit_events" in inspect(engine).get_table_names()
    assert {"before", "after"}.issubset(
        {column["name"] for column in inspect(engine).get_columns("audit_events")}
    )
    migrate(url, "downgrade", "0003")
    assert "audit_events" in inspect(engine).get_table_names()
    assert "before" not in {
        column["name"] for column in inspect(engine).get_columns("audit_events")
    }
    assert "users" in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM assignments")) == 2
    migrate(url, "upgrade", "head")
    migrate(url, "downgrade", "0001")
    assert "users" not in inspect(engine).get_table_names()
    migrate(url, "upgrade", "head")
    migrate(url, "downgrade", "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()


def test_snapshot_upgrade_preserves_existing_audit_events(tmp_path):
    url = "sqlite:///" + str(tmp_path / "existing_audit.db")
    migrate(url, "upgrade", "0003")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (username, password_hash, role) VALUES ('legacy', 'synthetic', 'admin')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO audit_events (actor_id, actor_username, action, entity_type, entity_id) "
                "VALUES (1, 'legacy', 'student.created', 'student', 1)"
            )
        )
    migrate(url, "upgrade", "head")
    migrate(url, "check")
    with engine.connect() as connection:
        event = connection.execute(text("SELECT * FROM audit_events")).mappings().one()
        assert event["actor_username"] == "legacy"
        assert event["action"] == "student.created"
        assert event["before"] is None and event["after"] is None
    migrate(url, "downgrade", "0003")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM audit_events")) == 1
    migrate(url, "upgrade", "head")
    migrate(url, "check")
    engine.dispose()
