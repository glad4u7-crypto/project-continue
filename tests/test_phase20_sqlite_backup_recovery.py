from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import sqlite3
from pathlib import Path

import pytest

from database import Database, ProjectRepository
from services.backup_operations import BackupOperations


def prepared(tmp_path):
    live = tmp_path / "live" / "project.sqlite3"
    db = Database(live)
    repo = ProjectRepository(db)
    repo.initialize()
    repo.create_project("p1", "Recovery test")
    ops = BackupOperations(db, tmp_path / "backups")
    return db, repo, ops


def test_backup_manifest_checksum_inventory_and_preview_are_read_only(tmp_path):
    db, repo, ops = prepared(tmp_path)
    backup = ops.create_backup()
    verified = ops.verify_backup(backup)
    assert verified["verified"] is True
    assert verified["sha256"] == hashlib.sha256(backup.read_bytes()).hexdigest()
    assert verified["schema_version"] == 2
    inventory = ops.inventory_backups()
    assert inventory["count"] == 1
    assert inventory["items"][0]["status"] == "verified"
    destination = tmp_path / "restore" / "preview.sqlite3"
    preview = ops.preview_restore(backup, destination)
    assert preview["status"] == "PREVIEW_ONLY"
    assert preview["writes_performed"] is False
    assert not destination.exists()
    db.close()


def test_corrupt_or_truncated_backup_is_rejected(tmp_path):
    db, repo, ops = prepared(tmp_path)
    backup = ops.create_backup()
    payload = backup.read_bytes()
    backup.write_bytes(payload[: max(1, len(payload) // 2)])
    with pytest.raises((ValueError, sqlite3.DatabaseError)):
        ops.verify_backup(backup)
    with pytest.raises((ValueError, sqlite3.DatabaseError)):
        ops.preview_restore(backup, tmp_path / "restore.sqlite3")
    assert ops.inventory_backups()["items"][0]["status"] == "invalid"
    db.close()


def test_interrupted_restore_rolls_back_partial_destination(tmp_path, monkeypatch):
    db, repo, ops = prepared(tmp_path)
    backup = ops.create_backup()
    destination = tmp_path / "restore" / "interrupted.sqlite3"
    original = Database.connection

    def interrupted(self):
        raise RuntimeError("simulated restore interruption")

    monkeypatch.setattr(Database, "connection", interrupted)
    with pytest.raises(RuntimeError, match="interruption"):
        ops.restore_drill(backup, destination)
    assert not destination.exists()
    monkeypatch.setattr(Database, "connection", original)
    assert ops.verify_backup(backup)["verified"]
    db.close()


def test_restore_never_overwrites_existing_destination_or_live_database(tmp_path):
    db, repo, ops = prepared(tmp_path)
    backup = ops.create_backup()
    existing = tmp_path / "restore" / "existing.sqlite3"
    existing.parent.mkdir()
    existing.write_text("preserve-me", encoding="utf-8")
    with pytest.raises(FileExistsError):
        ops.restore_drill(backup, existing)
    assert existing.read_text(encoding="utf-8") == "preserve-me"
    with pytest.raises(ValueError, match="live database"):
        ops.restore_drill(backup, db.path)
    db.close()


def test_retention_requires_fresh_preview_confirmation_and_approval(tmp_path):
    db, repo, ops = prepared(tmp_path)
    backup = ops.create_backup()
    old = datetime.now(timezone.utc) - timedelta(days=45)
    os.utime(backup, (old.timestamp(), old.timestamp()))
    manifest = ops._manifest_path(backup)
    os.utime(manifest, (old.timestamp(), old.timestamp()))
    preview = ops.preview_retention(keep_days=30)
    assert preview["candidate_count"] == 1
    with pytest.raises(PermissionError):
        ops.apply_retention(preview, confirm=True)
    assert backup.exists()
    assert ops.apply_retention(preview, confirm=True, approval_id="reviewed-delete-001") == [str(backup)]
    assert not backup.exists()
    assert not manifest.exists()
    db.close()


def test_stale_or_forged_retention_preview_cannot_delete_changed_backup(tmp_path):
    db, repo, ops = prepared(tmp_path)
    backup = ops.create_backup()
    old = datetime.now(timezone.utc) - timedelta(days=45)
    os.utime(backup, (old.timestamp(), old.timestamp()))
    manifest = ops._manifest_path(backup)
    os.utime(manifest, (old.timestamp(), old.timestamp()))
    preview = ops.preview_retention(keep_days=30)
    backup.write_bytes(backup.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="changed after preview"):
        ops.apply_retention(preview, confirm=True, approval_id="reviewed-delete-002")
    assert backup.exists()
    db.close()


def test_destructive_operation_gate_binds_approval_to_exact_sha_without_mutation(tmp_path):
    db, repo, ops = prepared(tmp_path)
    target = Path(db.path)
    before = target.read_bytes()
    digest = hashlib.sha256(before).hexdigest()
    result = ops.authorize_destructive_operation(
        "overwrite_database", target, approval_id="human-review-003",
        expected_sha256=digest,
    )
    assert result["authorized"] is True
    assert result["mutation_performed"] is False
    assert target.read_bytes() == before
    with pytest.raises(PermissionError):
        ops.authorize_destructive_operation(
            "overwrite_database", target, approval_id="human-review-003",
            expected_sha256="0" * 64,
        )
    db.close()


def test_backup_does_not_touch_drive_like_sentinel(tmp_path):
    db, repo, ops = prepared(tmp_path)
    drive_root = tmp_path / "drive" / "MyDrive"
    drive_root.mkdir(parents=True)
    sentinel = drive_root / "keep.txt"
    sentinel.write_text("do not mount or modify", encoding="utf-8")
    ops.create_backup()
    assert sentinel.read_text(encoding="utf-8") == "do not mount or modify"
    assert not (drive_root / "project-continue.sqlite3").exists()
    db.close()


def test_restore_rejects_symlink_destination_and_symlink_backup_root(tmp_path):
    db, repo, ops = prepared(tmp_path)
    backup = ops.create_backup()
    outside = tmp_path / "outside.sqlite3"
    outside.write_text("preserve", encoding="utf-8")
    link = tmp_path / "restore-link.sqlite3"
    link.symlink_to(outside)
    with pytest.raises(ValueError, match="symbolic links"):
        ops.restore_drill(backup, link)
    assert outside.read_text(encoding="utf-8") == "preserve"
    db.close()


def test_backup_verification_rejects_symlink_alias(tmp_path):
    db, repo, ops = prepared(tmp_path)
    backup = ops.create_backup()
    alias = tmp_path / "backups" / "project-continue-alias.sqlite3"
    alias.symlink_to(backup)
    with pytest.raises(ValueError, match="symbolic links"):
        ops.verify_backup(alias)
    with pytest.raises(ValueError, match="symbolic link"):
        Database.verify_backup(alias)
    db.close()


def test_backup_root_nested_under_live_directory_is_rejected(tmp_path):
    db = Database(tmp_path / "live" / "project.sqlite3")
    with pytest.raises(ValueError, match="separate from the live database directory"):
        BackupOperations(db, tmp_path / "live" / "backups")
    db.close()


def test_backup_root_symlink_is_rejected(tmp_path):
    db, repo, ops = prepared(tmp_path)
    actual = tmp_path / "actual-backups"
    actual.mkdir()
    alias = tmp_path / "backup-alias"
    alias.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic links"):
        BackupOperations(db, alias)
    db.close()


def test_schema_version_mismatch_is_rejected(tmp_path):
    db, repo, ops = prepared(tmp_path)
    bad = tmp_path / "backups" / "project-continue-bad.sqlite3"
    bad.parent.mkdir(exist_ok=True)
    with sqlite3.connect(bad) as connection:
        connection.execute("CREATE TABLE schema_version(id INTEGER PRIMARY KEY, version INTEGER)")
        connection.execute("INSERT INTO schema_version VALUES(1, 1)")
    with pytest.raises(ValueError, match="schema version"):
        ops.inspect_sqlite(bad)
    db.close()
