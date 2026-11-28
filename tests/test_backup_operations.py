from datetime import datetime, timedelta, timezone
import os
import pytest

from database import Database, ProjectRepository, sha256_file
from services.backup_operations import BackupOperations


def test_backup_integrity_restore_drill_and_no_overwrite(tmp_path):
    live = tmp_path / "live" / "db.sqlite3"
    db = Database(live)
    repo = ProjectRepository(db)
    repo.initialize()
    repo.create_project("p1", "Project one")
    ops = BackupOperations(db, tmp_path / "backups")
    backup = ops.create_backup()
    assert Database.verify_backup(backup)
    restored = ops.restore_drill(backup, tmp_path / "restore" / "copy.sqlite3")
    restored_db = Database(restored)
    assert ProjectRepository(restored_db).get_project("p1")["name"] == "Project one"
    with pytest.raises(FileExistsError):
        ops.restore_drill(backup, restored)
    with pytest.raises(ValueError, match="live database"):
        ops.restore_drill(backup, live)
    restored_db.close()
    db.close()


def test_retention_is_preview_first_and_namespace_limited(tmp_path):
    db = Database(tmp_path / "live.sqlite3")
    repo = ProjectRepository(db)
    repo.initialize()
    ops = BackupOperations(db, tmp_path / "backups")
    backup = ops.create_backup()
    old = datetime.now(timezone.utc) - timedelta(days=45)
    os.utime(backup, (old.timestamp(), old.timestamp()))
    preview = ops.preview_retention(keep_days=30)
    assert preview["candidate_count"] == 1
    with pytest.raises(PermissionError):
        ops.apply_retention(preview)
    assert backup.exists()
    assert ops.apply_retention(preview, confirm=True) == [str(backup)]
    assert not backup.exists()
    db.close()


def test_backup_root_cannot_be_live_database_directory(tmp_path):
    db = Database(tmp_path / "live.sqlite3")
    with pytest.raises(ValueError, match="live database directory"):
        BackupOperations(db, tmp_path)
    db.close()


def test_retention_rejects_untrusted_paths(tmp_path):
    db = Database(tmp_path / "live.sqlite3")
    ops = BackupOperations(db, tmp_path / "backups")
    with pytest.raises(ValueError, match="namespace"):
        ops.apply_retention({"candidates": [str(tmp_path / "important.txt")]}, confirm=True)
    db.close()


def test_inventory_reports_managed_backups_and_ignores_unmanaged_files(tmp_path):
    db = Database(tmp_path / "live" / "db.sqlite3")
    ProjectRepository(db).initialize()
    ops = BackupOperations(db, tmp_path / "backups")
    backup = ops.create_backup()
    (ops.root / "notes.txt").write_text("not a backup", encoding="utf-8")
    (ops.root / "project-continue-malformed.sqlite3").write_bytes(b"not sqlite")
    inventory = ops.inventory_backups()
    assert inventory["preview_only"] is True
    assert inventory["entry_count"] == 2
    by_name = {entry["name"]: entry for entry in inventory["entries"]}
    valid = by_name[backup.name]
    assert valid["sha256"] == sha256_file(backup)
    assert valid["integrity_verified"] is True
    assert valid["eligible_for_restore"] is True
    damaged = by_name["project-continue-malformed.sqlite3"]
    assert damaged["integrity_verified"] is False
    assert damaged["eligible_for_restore"] is False
    assert damaged["error_type"] in {"DatabaseError", "OperationalError"}
    db.close()


def test_restore_preview_is_read_only_and_does_not_create_destination(tmp_path):
    db = Database(tmp_path / "live" / "db.sqlite3")
    repo = ProjectRepository(db)
    repo.initialize()
    repo.create_project("preview-project", "Preview only")
    ops = BackupOperations(db, tmp_path / "backups")
    backup = ops.create_backup()
    before = sha256_file(backup)
    destination = tmp_path / "restore-preview" / "candidate.sqlite3"
    preview = ops.preview_restore(backup, destination)
    assert preview == {
        "preview_only": True, "eligible": True, "source_name": backup.name,
        "source_size_bytes": backup.stat().st_size, "source_sha256": before,
        "destination_name": destination.name, "destination_parent_exists": False,
        "destination_exists": False, "integrity_verified": True, "actions_performed": (),
    }
    assert sha256_file(backup) == before
    assert backup.exists()
    assert not destination.exists()
    assert not destination.parent.exists()
    db.close()


def test_restore_preview_rejects_live_existing_and_unmanaged_destinations(tmp_path):
    db = Database(tmp_path / "live" / "db.sqlite3")
    ProjectRepository(db).initialize()
    ops = BackupOperations(db, tmp_path / "backups")
    backup = ops.create_backup()
    with pytest.raises(ValueError, match="live database"):
        ops.preview_restore(backup, db.path)
    existing = tmp_path / "existing.sqlite3"
    existing.write_bytes(b"preserve")
    with pytest.raises(FileExistsError):
        ops.preview_restore(backup, existing)
    with pytest.raises(ValueError, match="managed backup"):
        ops.preview_restore(tmp_path / "unmanaged.sqlite3", tmp_path / "new.sqlite3")
    assert existing.read_bytes() == b"preserve"
    db.close()


def test_inventory_ignores_symlinked_backup(tmp_path):
    db = Database(tmp_path / "live" / "db.sqlite3")
    ProjectRepository(db).initialize()
    ops = BackupOperations(db, tmp_path / "backups")
    backup = ops.create_backup()
    link = ops.root / "project-continue-linked.sqlite3"
    try:
        link.symlink_to(backup)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks are unavailable on this runner")
    inventory = ops.inventory_backups()
    assert [entry["name"] for entry in inventory["entries"]] == [backup.name]
    db.close()
