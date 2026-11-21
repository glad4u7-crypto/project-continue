"""Safe backup orchestration, preview-first retention and isolated restore drills."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

from database.connection import Database


class BackupOperations:
    """Operations around Database.backup; never overwrites or restores live data."""

    PREFIX = "project-continue-"
    SUFFIX = ".sqlite3"

    def __init__(self, database: Database, backup_root: str | Path, *, clock=None):
        self.database = database
        self.root = Path(backup_root).expanduser().resolve()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        source = Path(database.path).expanduser().resolve()
        if database.path != ":memory:" and self.root == source.parent:
            raise ValueError("Backup directory must differ from the live database directory")

    def create_backup(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        stamp = self.clock().astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        target = self.root / f"{self.PREFIX}{stamp}{self.SUFFIX}"
        created = self.database.backup(target)
        if not Database.verify_backup(created):
            created.unlink(missing_ok=True)
            raise sqlite3.DatabaseError("Backup verification failed")
        return created

    def preview_retention(self, *, keep_days=30) -> dict:
        if isinstance(keep_days, bool) or not isinstance(keep_days, int) or not 1 <= keep_days <= 3650:
            raise ValueError("keep_days must be between 1 and 3650")
        cutoff = self.clock().astimezone(timezone.utc) - timedelta(days=keep_days)
        candidates = []
        if self.root.exists():
            for item in self.root.iterdir():
                if (item.is_file() and not item.is_symlink()
                        and item.name.startswith(self.PREFIX) and item.name.endswith(self.SUFFIX)):
                    if datetime.fromtimestamp(item.stat().st_mtime, timezone.utc) < cutoff:
                        candidates.append(str(item.resolve()))
        return {"keep_days": keep_days, "cutoff": cutoff.isoformat(),
                "candidate_count": len(candidates), "candidates": sorted(candidates)}

    def apply_retention(self, preview: dict, *, confirm=False) -> list[str]:
        if confirm is not True:
            raise PermissionError("Explicit confirm=True is required for retention deletion")
        if not isinstance(preview, dict) or not isinstance(preview.get("candidates"), list):
            raise ValueError("A valid retention preview is required")
        deleted = []
        for raw in preview["candidates"]:
            path = Path(raw)
            if path.parent.resolve() != self.root or path.name.startswith(self.PREFIX) is False or not path.name.endswith(self.SUFFIX):
                raise ValueError("Retention candidate is outside the managed backup namespace")
            if path.is_symlink() or not path.is_file():
                continue
            path.unlink()
            deleted.append(str(path))
        return deleted

    def restore_drill(self, backup_path: str | Path, destination: str | Path) -> Path:
        raw_source = Path(backup_path).expanduser()
        if raw_source.is_symlink():
            raise ValueError("Restore source must not be a symbolic link")
        source = raw_source.resolve()
        target = Path(destination).expanduser().resolve()
        if source.parent != self.root or not source.name.startswith(self.PREFIX) or not source.name.endswith(self.SUFFIX):
            raise ValueError("Restore source must be a managed backup")
        live = Path(self.database.path).expanduser().resolve()
        if self.database.path != ":memory:" and target == live:
            raise ValueError("Restore drill cannot overwrite the live database")
        if target.exists():
            raise FileExistsError("Restore destination already exists")
        if target == source:
            raise ValueError("Restore destination must differ from backup source")
        if not Database.verify_backup(source):
            raise sqlite3.DatabaseError("Restore source failed integrity verification")
        target.parent.mkdir(parents=True, exist_ok=True)
        destination_db = Database(target)
        try:
            # Use SQLite's backup API for a consistent, isolated copy.
            from urllib.parse import quote
            source_uri = f"file:{quote(str(source), safe='/:')}?mode=ro"
            with sqlite3.connect(source_uri, uri=True) as src:
                with destination_db.connection() as dst:
                    src.backup(dst)
            if not Database.verify_backup(target):
                raise sqlite3.DatabaseError("Restored database failed integrity verification")
            return target
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        finally:
            destination_db.close()
