import sqlite3

import pytest

pytestmark = pytest.mark.database

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


def test_backup_preserves_database_and_passes_integrity_check(tmp_path):
    source_path = tmp_path / "source" / "project.db"
    backup_path = tmp_path / "backups" / "project-backup.db"
    database = ConnectionDatabase(source_path)
    with database.connection() as connection:
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO sample(value) VALUES (?)", ("preserved",))

    created = database.backup(backup_path)

    assert created == backup_path
    assert ConnectionDatabase.verify_backup(backup_path) is True
    with sqlite3.connect(backup_path) as connection:
        assert connection.execute("SELECT value FROM sample").fetchone()[0] == "preserved"


def test_backup_does_not_overwrite_existing_destination(tmp_path):
    database = ConnectionDatabase(tmp_path / "source.db")
    destination = tmp_path / "existing-backup.db"
    destination.write_text("keep this file", encoding="utf-8")

    with pytest.raises(FileExistsError):
        database.backup(destination)

    assert destination.read_text(encoding="utf-8") == "keep this file"


def test_backup_rejects_source_as_destination(tmp_path):
    source = tmp_path / "source.db"
    database = ConnectionDatabase(source)
    with database.connection() as connection:
        connection.execute("CREATE TABLE sample (id INTEGER)")

    with pytest.raises(ValueError, match="differ"):
        database.backup(source)


def test_backup_file_permissions_are_owner_only_on_posix(tmp_path):
    import os
    import stat

    if os.name != "posix":
        pytest.skip("POSIX file permissions are not available")
    database = ConnectionDatabase(tmp_path / "source.db")
    backup = database.backup(tmp_path / "backup.db")
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600


def test_verify_backup_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        ConnectionDatabase.verify_backup(tmp_path / "missing.db")


def test_backup_rejects_empty_destination(tmp_path):
    database = ConnectionDatabase(tmp_path / "source.db")
    with pytest.raises(ValueError, match="must not be empty"):
        database.backup("")
