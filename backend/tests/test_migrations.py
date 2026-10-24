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
        if legacy:
            connection.execute(text("DROP TABLE alembic_version"))
    if legacy:
        migrate(url, "stamp", "0001")
    migrate(url, "upgrade", "head")
    migrate(url, "check")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT full_name FROM students")) == "Test Student"
    assert "repair_requests" in inspect(engine).get_table_names()
    migrate(url, "downgrade", "0001")
    assert "users" not in inspect(engine).get_table_names()
    migrate(url, "upgrade", "head")
    migrate(url, "downgrade", "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()
