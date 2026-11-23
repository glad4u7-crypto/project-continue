"""Atomic and concurrency-safe repository initialization tests."""
from concurrent.futures import ThreadPoolExecutor

import pytest

from database import Database, ProjectRepository
from database.schema import SCHEMA_VERSION


def test_initialize_migrates_legacy_tasks_table(tmp_path):
    database = Database(tmp_path / "legacy.sqlite3")
    with database.connection() as connection:
        connection.execute(
            "CREATE TABLE schema_version (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL)"
        )
        connection.execute("INSERT INTO schema_version VALUES (1, 1)")
        connection.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY)")

    ProjectRepository(database).initialize()

    with database.connection() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(tasks)")}
        version = connection.execute(
            "SELECT version FROM schema_version WHERE id=1"
        ).fetchone()["version"]
    assert "assignee" in columns
    assert version == SCHEMA_VERSION


def test_initialize_rejects_newer_schema_and_rolls_back(tmp_path):
    database = Database(tmp_path / "future.sqlite3")
    with database.connection() as connection:
        connection.execute(
            "CREATE TABLE schema_version (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL)"
        )
        connection.execute("INSERT INTO schema_version VALUES (1, ?)", (SCHEMA_VERSION + 1,))

    with pytest.raises(RuntimeError, match="newer than this application"):
        ProjectRepository(database).initialize()

    with database.connection() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        version = connection.execute(
            "SELECT version FROM schema_version WHERE id=1"
        ).fetchone()["version"]
    assert "projects" not in tables
    assert version == SCHEMA_VERSION + 1


def test_concurrent_initialization_is_serialized(tmp_path):
    path = tmp_path / "concurrent.sqlite3"

    def initialize():
        database = Database(path, timeout=10)
        try:
            ProjectRepository(database).initialize()
            return database.health_check()
        finally:
            database.close()

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: initialize(), range(4)))

    assert results == [True, True, True, True]
