"""SHA-256 manifest tests for disposable SQLite backups."""
import hashlib
import sqlite3

import pytest

from database import (
    Database,
    create_verified_backup,
    sha256_file,
    verify_backup_checksum,
    inventory_backups,
    preview_backup_restore,
    ProjectRepository,
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



def _create_application_backup(destination):
    source = Database(destination.parent / "source.sqlite3")
    repository = ProjectRepository(source)
    repository.initialize()
    repository.create_project("preview-project", "Preview project")
    manifest = create_verified_backup(source, destination)
    source.close()
    return manifest


def test_backup_inventory_lists_only_regular_backup_files_and_checks_integrity(tmp_path):
    backup_dir = tmp_path / "backup-inventory"
    backup_dir.mkdir()
    manifest = _create_application_backup(backup_dir / "project.sqlite3")
    (backup_dir / "notes.txt").write_text("not a database backup", encoding="utf-8")
    (backup_dir / "alias.sqlite3").symlink_to(manifest.path)

    inventory = inventory_backups(backup_dir)
    assert len(inventory) == 1
    item = inventory[0]
    assert item.name == "project.sqlite3"
    assert item.size_bytes == manifest.size_bytes
    assert item.sha256 == manifest.sha256
    assert item.integrity_report is not None
    assert item.integrity_report.healthy is True
    assert item.inspection_error is None


def test_backup_inventory_reports_invalid_database_without_mutating_it(tmp_path):
    backup_dir = tmp_path / "backup-inventory"
    backup_dir.mkdir()
    invalid = backup_dir / "broken.db"
    invalid.write_bytes(b"not sqlite data")
    before = hashlib.sha256(invalid.read_bytes()).hexdigest()

    inventory = inventory_backups(backup_dir)
    assert len(inventory) == 1
    assert inventory[0].inspection_error == "sqlite_inspection_failed"
    assert inventory[0].integrity_report is None
    assert hashlib.sha256(invalid.read_bytes()).hexdigest() == before


def test_backup_inventory_does_not_create_missing_directory_or_follow_symlink(tmp_path):
    missing = tmp_path / "missing-backups"
    with pytest.raises(FileNotFoundError):
        inventory_backups(missing)
    assert not missing.exists()

    real = tmp_path / "real-backups"
    real.mkdir()
    alias = tmp_path / "backup-alias"
    alias.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="must not be a symlink"):
        inventory_backups(alias)


def test_restore_preview_is_read_only_and_never_performs_restore(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    manifest = _create_application_backup(backup_dir / "verified.sqlite3")
    before = hashlib.sha256(manifest.path.read_bytes()).hexdigest()

    preview = preview_backup_restore(manifest.path, manifest.sha256)

    assert preview.checksum_matches is True
    assert preview.eligible_for_manual_restore_review is True
    assert preview.reason == "verified_preview_only"
    assert preview.integrity_report is not None
    assert preview.integrity_report.healthy is True
    assert preview.restore_performed is False
    assert hashlib.sha256(manifest.path.read_bytes()).hexdigest() == before
    assert not (backup_dir / "restored.sqlite3").exists()


def test_restore_preview_rejects_checksum_mismatch_without_database_inspection(tmp_path):
    path = tmp_path / "backup.sqlite3"
    path.write_bytes(b"untrusted backup bytes")
    preview = preview_backup_restore(path, hashlib.sha256(b"different").hexdigest())

    assert preview.checksum_matches is False
    assert preview.integrity_report is None
    assert preview.eligible_for_manual_restore_review is False
    assert preview.reason == "checksum_mismatch"
    assert preview.restore_performed is False


def test_restore_preview_rejects_corrupt_and_unsupported_schema_backups(tmp_path):
    corrupt = tmp_path / "corrupt.sqlite3"
    corrupt.write_bytes(b"not sqlite")
    corrupt_preview = preview_backup_restore(corrupt, sha256_file(corrupt))
    assert corrupt_preview.reason == "sqlite_inspection_failed"
    assert corrupt_preview.eligible_for_manual_restore_review is False

    newer = tmp_path / "newer.sqlite3"
    database = Database(newer)
    ProjectRepository(database).initialize()
    with database.connection() as connection:
        connection.execute("UPDATE schema_version SET version = 999 WHERE id = 1")
    database.close()
    newer_preview = preview_backup_restore(newer, sha256_file(newer))
    assert newer_preview.reason == "schema_version_unsupported"
    assert newer_preview.eligible_for_manual_restore_review is False


def test_restore_preview_rejects_symlink_and_missing_path(tmp_path):
    actual = tmp_path / "actual.sqlite3"
    actual.write_bytes(b"sqlite fixture")
    alias = tmp_path / "alias.sqlite3"
    alias.symlink_to(actual)
    with pytest.raises(ValueError, match="does not follow symlinks"):
        preview_backup_restore(alias, sha256_file(actual))
    with pytest.raises(FileNotFoundError):
        preview_backup_restore(tmp_path / "missing.sqlite3", "0" * 64)
