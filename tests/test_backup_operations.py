from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import os
import pytest

from database import Database, ProjectRepository, sha256_file
from services.backup_operations import BackupOperations


def _restore_approval(ops, backup, destination):
    return ops.issue_restore_approval(
        backup, destination, approved_by="test-operator",
        confirmation=f"APPROVE RESTORE {Path(destination).name} FROM {Path(backup).name}",
    )


def test_backup_integrity_restore_drill_and_no_overwrite(tmp_path):
    live = tmp_path / "live" / "db.sqlite3"
    db = Database(live)
    repo = ProjectRepository(db)
    repo.initialize()
    repo.create_project("p1", "Project one")
    ops = BackupOperations(db, tmp_path / "backups")
    backup = ops.create_backup()
    assert Database.verify_backup(backup)
    destination = tmp_path / "restore" / "copy.sqlite3"
    restored = ops.restore_drill(backup, destination, approval=_restore_approval(ops, backup, destination))
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
    with pytest.raises(PermissionError, match="Boolean confirmation"):
        ops.apply_retention(preview, confirm=True)
    approval = ops.issue_delete_approval(
        preview, backup, approved_by="test-operator",
        confirmation=f"APPROVE DELETE {backup.name}",
    )
    assert ops.apply_retention(preview, approvals={str(backup): approval}) == [str(backup)]
    assert not backup.exists()
    assert [event["event"] for event in ops.approval_audit] == ["approval_issued", "approval_consumed"]
    with pytest.raises(PermissionError):
        ops.apply_retention(preview, approvals={str(backup): approval})
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
    unmanaged = tmp_path / "unmanaged.sqlite3"
    unmanaged.write_bytes(b"unmanaged fixture")
    with pytest.raises(ValueError, match="managed backup"):
        ops.preview_restore(unmanaged, tmp_path / "new.sqlite3")
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



def test_interrupted_restore_removes_partial_file_and_new_parent_directories(tmp_path, monkeypatch):
    db = Database(tmp_path / "live" / "db.sqlite3")
    repository = ProjectRepository(db)
    repository.initialize()
    repository.create_project("interrupt-project", "Preserve source")
    ops = BackupOperations(db, tmp_path / "backups")
    backup = ops.create_backup()
    destination = tmp_path / "interrupted" / "nested" / "restored.sqlite3"

    original_connect = sqlite3.connect
    readonly_calls = 0

    class InterruptedSource:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def backup(self, target_connection):
            raise RuntimeError("injected interruption during SQLite backup copy")

    def interrupt_copy(database, *args, **kwargs):
        nonlocal readonly_calls
        if isinstance(database, str) and database.startswith("file:") and "mode=ro" in database:
            readonly_calls += 1
            if readonly_calls == 3:
                return InterruptedSource()
        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", interrupt_copy)
    with pytest.raises(RuntimeError, match="injected interruption"):
        ops.restore_drill(backup, destination, approval=_restore_approval(ops, backup, destination))

    assert backup.exists()
    assert Database.verify_backup(backup) is True
    assert repository.get_project("interrupt-project")["name"] == "Preserve source"
    assert not destination.exists()
    assert not destination.parent.exists()
    assert not (tmp_path / "interrupted").exists()
    db.close()


def test_restore_verification_failure_rolls_back_restored_file(tmp_path, monkeypatch):
    db = Database(tmp_path / "live" / "db.sqlite3")
    repository = ProjectRepository(db)
    repository.initialize()
    repository.create_project("rollback-project", "Keep live data")
    ops = BackupOperations(db, tmp_path / "backups")
    backup = ops.create_backup()
    destination = tmp_path / "rollback" / "nested" / "restored.sqlite3"

    original_verify = Database.verify_backup
    verification_calls = 0

    def fail_after_copy(path):
        nonlocal verification_calls
        verification_calls += 1
        if verification_calls == 3:
            return False
        return original_verify(path)

    monkeypatch.setattr(Database, "verify_backup", staticmethod(fail_after_copy))
    with pytest.raises(sqlite3.DatabaseError, match="Restored database failed integrity"):
        ops.restore_drill(backup, destination, approval=_restore_approval(ops, backup, destination))

    assert verification_calls == 2
    assert backup.exists()
    assert not destination.exists()
    assert not destination.parent.exists()
    assert not (tmp_path / "rollback").exists()
    assert repository.get_project("rollback-project")["name"] == "Keep live data"
    db.close()



def test_idempotent_restore_replay_returns_identical_copy_without_duplicate_rows(tmp_path):
    live_db = Database(tmp_path / "live" / "db.sqlite3")
    source_repository = ProjectRepository(live_db)
    source_repository.initialize()
    source_repository.create_project("stable-project", "Backup source")
    source_repository.create_task("stable-task", "stable-project", "One task")
    ops = BackupOperations(live_db, tmp_path / "backups")
    backup = ops.create_backup()
    destination = tmp_path / "idempotent" / "nested" / "restored.sqlite3"

    first = ops.restore_drill_idempotent(backup, destination, approval=_restore_approval(ops, backup, destination))
    first_digest = sha256_file(first)
    second = ops.restore_drill_idempotent(backup, destination)

    assert first == second
    assert sha256_file(second) == first_digest
    restored_db = Database(second)
    restored_repository = ProjectRepository(restored_db)
    assert [item["id"] for item in restored_repository.list_projects()] == ["stable-project"]
    assert [item["id"] for item in restored_repository.list_tasks("stable-project")] == ["stable-task"]
    restored_db.close()
    live_db.close()


def test_idempotent_restore_never_overwrites_existing_rows(tmp_path):
    live_db = Database(tmp_path / "live" / "db.sqlite3")
    source_repository = ProjectRepository(live_db)
    source_repository.initialize()
    source_repository.create_project("same-project", "Backup version")
    ops = BackupOperations(live_db, tmp_path / "backups")
    backup = ops.create_backup()

    destination = tmp_path / "existing" / "restored.sqlite3"
    existing_db = Database(destination)
    existing_repository = ProjectRepository(existing_db)
    existing_repository.initialize()
    existing_repository.create_project("same-project", "Existing destination row")
    existing_db.close()
    before = sha256_file(destination)

    with pytest.raises(FileExistsError, match="different data"):
        ops.restore_drill_idempotent(backup, destination)

    assert sha256_file(destination) == before
    reopened = Database(destination)
    assert ProjectRepository(reopened).get_project("same-project")["name"] == "Existing destination row"
    reopened.close()
    live_db.close()


def test_idempotent_restore_still_rejects_live_database_target(tmp_path):
    live_db = Database(tmp_path / "live" / "db.sqlite3")
    ProjectRepository(live_db).initialize()
    ops = BackupOperations(live_db, tmp_path / "backups")
    backup = ops.create_backup()

    with pytest.raises(ValueError, match="live database"):
        ops.restore_drill_idempotent(backup, live_db.path)
    assert Database.verify_backup(backup) is True
    live_db.close()



def test_restore_requires_exact_one_time_source_and_destination_approval(tmp_path):
    db = Database(tmp_path / "live.sqlite3")
    ProjectRepository(db).initialize()
    ops = BackupOperations(db, tmp_path / "backups")
    backup = ops.create_backup()
    destination = tmp_path / "restore" / "copy.sqlite3"
    with pytest.raises(PermissionError, match="explicit one-time restore approval"):
        ops.restore_drill(backup, destination)
    assert not destination.exists()
    with pytest.raises(PermissionError, match="Exact source-and-target"):
        ops.issue_restore_approval(
            backup, destination, approved_by="operator", confirmation="APPROVE RESTORE",
        )
    approval = _restore_approval(ops, backup, destination)
    restored = ops.restore_drill(backup, destination, approval=approval)
    assert Database.verify_backup(restored)
    other = tmp_path / "restore" / "other.sqlite3"
    with pytest.raises(PermissionError, match="already consumed"):
        ops.restore_drill(backup, other, approval=approval)
    assert not other.exists()
    db.close()


def test_delete_approval_is_target_specific_and_requires_exact_phrase(tmp_path):
    db = Database(tmp_path / "live.sqlite3")
    ops = BackupOperations(db, tmp_path / "backups")
    backup = ops.create_backup()
    old = datetime.now(timezone.utc) - timedelta(days=45)
    os.utime(backup, (old.timestamp(), old.timestamp()))
    preview = ops.preview_retention(keep_days=30)
    with pytest.raises(PermissionError, match="Exact target-specific"):
        ops.issue_delete_approval(
            preview, backup, approved_by="operator", confirmation="yes",
        )
    with pytest.raises(PermissionError, match="named approver"):
        ops.issue_delete_approval(
            preview, backup, approved_by=" ", confirmation=f"APPROVE DELETE {backup.name}",
        )
    approval = ops.issue_delete_approval(
        preview, backup, approved_by="operator",
        confirmation=f"APPROVE DELETE {backup.name}",
    )
    other_preview = dict(preview, keep_days=31)
    with pytest.raises(PermissionError, match="invalid, mismatched"):
        ops.apply_retention(other_preview, approvals={str(backup): approval})
    assert backup.exists()
    db.close()


def test_delete_approval_cannot_be_replayed_or_used_for_another_target(tmp_path):
    db = Database(tmp_path / "live.sqlite3")
    ops = BackupOperations(db, tmp_path / "backups")
    first = ops.create_backup()
    second = ops.create_backup()
    old = datetime.now(timezone.utc) - timedelta(days=45)
    os.utime(first, (old.timestamp(), old.timestamp()))
    os.utime(second, (old.timestamp(), old.timestamp()))
    preview = ops.preview_retention(keep_days=30)
    single_target_preview = dict(preview, candidates=[str(first.resolve())], candidate_count=1)
    approval = ops.issue_delete_approval(
        single_target_preview, first, approved_by="operator",
        confirmation=f"APPROVE DELETE {first.name}",
    )
    with pytest.raises(PermissionError):
        ops.apply_retention(single_target_preview, approvals={str(second): approval})
    assert first.exists() and second.exists()
    assert ops.apply_retention(single_target_preview, approvals={str(first): approval}) == [str(first)]
    with pytest.raises(PermissionError):
        ops.apply_retention(single_target_preview, approvals={str(first): approval})
    assert second.exists()
    db.close()
