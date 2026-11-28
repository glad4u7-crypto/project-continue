"""Read-only SQLite schema and integrity inspection tests."""
import hashlib
import sqlite3

import pytest

from database import Database, ProjectRepository, inspect_sqlite_database
from database.schema import SCHEMA_VERSION


pytestmark = pytest.mark.database


def _create_repository(path):
    database = Database(path)
    repository = ProjectRepository(database)
    repository.initialize()
    return database, repository


def test_inspection_reports_schema_integrity_and_foreign_keys_without_writes(tmp_path):
    path = tmp_path / "healthy.sqlite3"
    database, repository = _create_repository(path)
    repository.create_project("inspect-project", "Inspection fixture")
    repository.create_task("inspect-task", "inspect-project", "Integrity fixture")
    database.close()

    before = hashlib.sha256(path.read_bytes()).hexdigest()
    report = inspect_sqlite_database(path)
    after = hashlib.sha256(path.read_bytes()).hexdigest()

    assert report.schema_version == SCHEMA_VERSION
    assert report.expected_schema_version == SCHEMA_VERSION
    assert report.schema_version_supported is True
    assert report.integrity_results == ("ok",)
    assert report.foreign_key_violations == ()
    assert report.healthy is True
    assert before == after


def test_inspection_reports_missing_schema_version_without_migrating(tmp_path):
    path = tmp_path / "uninitialized.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")
    connection.commit()
    connection.close()

    before = hashlib.sha256(path.read_bytes()).hexdigest()
    report = inspect_sqlite_database(path)

    assert report.schema_version is None
    assert report.schema_version_supported is False
    assert report.integrity_results == ("ok",)
    assert report.healthy is False
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_inspection_reports_unsupported_newer_schema_version(tmp_path):
    path = tmp_path / "newer-schema.sqlite3"
    database, _ = _create_repository(path)
    with database.connection() as connection:
        connection.execute("UPDATE schema_version SET version = 999 WHERE id = 1")
    database.close()

    report = inspect_sqlite_database(path)
    assert report.schema_version == 999
    assert report.schema_version_supported is False
    assert report.integrity_results == ("ok",)
    assert report.healthy is False


def test_inspection_reports_foreign_key_violations(tmp_path):
    path = tmp_path / "foreign-key-violation.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
    connection.execute(
        "CREATE TABLE child (parent_id INTEGER REFERENCES parent(id))"
    )
    connection.execute("INSERT INTO child(parent_id) VALUES (404)")
    connection.commit()
    connection.close()

    report = inspect_sqlite_database(path)
    assert report.integrity_results == ("ok",)
    assert len(report.foreign_key_violations) == 1
    violation = report.foreign_key_violations[0]
    assert violation.table == "child"
    assert violation.parent_table == "parent"
    assert report.healthy is False


def test_inspection_rejects_missing_database_without_creating_it(tmp_path):
    path = tmp_path / "does-not-exist.sqlite3"
    with pytest.raises(FileNotFoundError):
        inspect_sqlite_database(path)
    assert not path.exists()
