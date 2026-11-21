from datetime import datetime, timedelta, timezone
import os
import pytest

from database import Database, ProjectRepository
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
