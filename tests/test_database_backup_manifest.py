"""SHA-256 manifest tests for disposable SQLite backups."""
import hashlib
import sqlite3

import pytest

from database import (
    Database,
    create_verified_backup,
    sha256_file,
    verify_backup_checksum,
)


pytestmark = pytest.mark.database


def test_verified_backup_returns_size_and_sha256_manifest(tmp_path):
    source = Database(tmp_path / "source.sqlite3")
    with source.connection() as connection:
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO sample(value) VALUES (?)", ("preserved",))

    destination = tmp_path / "backup" / "verified.sqlite3"
    manifest = create_verified_backup(source, destination)

    expected = hashlib.sha256(destination.read_bytes()).hexdigest()
    assert manifest.path == destination
    assert manifest.size_bytes == destination.stat().st_size
    assert manifest.sha256 == expected
    assert manifest.integrity_verified is True
    assert sha256_file(destination) == expected
    assert verify_backup_checksum(destination, expected) is True
    assert Database.verify_backup(destination) is True

    with sqlite3.connect(destination) as connection:
        assert connection.execute("SELECT value FROM sample").fetchone() == ("preserved",)
    source.close()


def test_backup_checksum_detects_changed_bytes(tmp_path):
    path = tmp_path / "backup.sqlite3"
    path.write_bytes(b"immutable backup fixture")
    expected = sha256_file(path)
    assert verify_backup_checksum(path, expected) is True

    path.write_bytes(b"tampered backup fixture")
    assert verify_backup_checksum(path, expected) is False


def test_checksum_rejects_malformed_digest_and_missing_file(tmp_path):
    path = tmp_path / "backup.sqlite3"
    path.write_bytes(b"fixture")
    for invalid in ("", "abc", "g" * 64, "A" * 64, None):
        with pytest.raises(ValueError, match="64 lowercase hexadecimal"):
            verify_backup_checksum(path, invalid)

    with pytest.raises(FileNotFoundError):
        sha256_file(tmp_path / "missing.sqlite3")


def test_verified_backup_refuses_existing_destination_without_overwrite(tmp_path):
    source = Database(tmp_path / "source.sqlite3")
    with source.connection() as connection:
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.execute("INSERT INTO sample VALUES ('source')")

    destination = tmp_path / "backup.sqlite3"
    destination.write_bytes(b"keep-existing-backup")
    with pytest.raises(FileExistsError):
        create_verified_backup(source, destination)
    assert destination.read_bytes() == b"keep-existing-backup"
    source.close()


def test_verified_backup_requires_database_instance(tmp_path):
    with pytest.raises(TypeError, match="Database instance"):
        create_verified_backup(object(), tmp_path / "backup.sqlite3")
