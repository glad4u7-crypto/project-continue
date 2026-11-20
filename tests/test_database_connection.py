import sqlite3

import pytest

from database import Database, ProjectRepository
from database.connection import Database as ConnectionDatabase


def test_health_check_and_row_factory(tmp_path):
    database = ConnectionDatabase(tmp_path / "nested" / "project.db")
    assert database.health_check() is True
    with database.connection() as connection:
        row = connection.execute("SELECT 7 AS value").fetchone()
        assert row["value"] == 7
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_connection_is_closed_after_context():
    database = ConnectionDatabase(":memory:")
    with database.connection() as connection:
        connection.execute("CREATE TABLE sample (id INTEGER)")
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")
    database.close()


def test_shared_memory_database_persists_across_repository_connections():
    database = Database(":memory:")
    try:
        repository = ProjectRepository(database)
        repository.initialize()
        repository.create_project("p-memory", "In-memory project")
        assert repository.get_project("p-memory")["name"] == "In-memory project"
        assert database.health_check() is True
    finally:
        database.close()


def test_transaction_commits_on_success(tmp_path):
    database = ConnectionDatabase(tmp_path / "commit.db")
    with database.connection() as connection:
        connection.execute("CREATE TABLE sample (value TEXT)")
    with database.transaction() as connection:
        connection.execute("INSERT INTO sample VALUES (?)", ("saved",))
    with database.connection() as connection:
        assert connection.execute("SELECT value FROM sample").fetchone()["value"] == "saved"


def test_transaction_rolls_back_on_error(tmp_path):
    database = ConnectionDatabase(tmp_path / "rollback.db")
    with database.connection() as connection:
        connection.execute("CREATE TABLE sample (value TEXT)")
    with pytest.raises(RuntimeError):
        with database.transaction() as connection:
            connection.execute("INSERT INTO sample VALUES (?)", ("not-saved",))
            raise RuntimeError("force rollback")
    with database.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM sample").fetchone()[0] == 0


def test_timeout_must_be_positive():
    with pytest.raises(ValueError):
        ConnectionDatabase(":memory:", timeout=0)
