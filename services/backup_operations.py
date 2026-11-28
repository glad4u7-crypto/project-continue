"""Safe backup orchestration, inventory, preview-first retention and restore drills."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

from database.backup import sha256_file
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

    def _is_managed_backup(self, item: Path) -> bool:
        return item.parent.resolve() == self.root and item.name.startswith(self.PREFIX) and item.name.endswith(self.SUFFIX)

    def create_backup(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        stamp = self.clock().astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        target = self.root / f"{self.PREFIX}{stamp}{self.SUFFIX}"
        created = self.database.backup(target)
        if not Database.verify_backup(created):
            created.unlink(missing_ok=True)
            raise sqlite3.DatabaseError("Backup verification failed")
        return created

    def inventory_backups(self) -> dict:
        """Return metadata-only inventory; ignore symlinks and unmanaged files."""
        entries = []
        if not self.root.is_dir():
            return {"backup_root": str(self.root), "entry_count": 0, "entries": (), "preview_only": True}
        for item in sorted(self.root.iterdir(), key=lambda candidate: candidate.name):
            if item.is_symlink() or not item.is_file() or not self._is_managed_backup(item):
                continue
            stat = item.stat(follow_symlinks=False)
            digest = None
            integrity_verified = False
            error_type = None
            try:
                digest = sha256_file(item)
                integrity_verified = Database.verify_backup(item)
                if not integrity_verified:
                    raise sqlite3.DatabaseError("Backup failed integrity verification")
            except (OSError, sqlite3.DatabaseError) as exc:
                error_type = type(exc).__name__
            entries.append({
                "name": item.name, "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "sha256": digest, "integrity_verified": integrity_verified,
                "eligible_for_restore": integrity_verified and digest is not None,
                "error_type": error_type,
            })
        return {"backup_root": str(self.root), "entry_count": len(entries), "entries": tuple(entries), "preview_only": True}

    def preview_restore(self, backup_path: str | Path, destination: str | Path) -> dict:
        """Validate a prospective restore without creating or changing any file."""
        raw_source = Path(backup_path).expanduser()
        if raw_source.is_symlink():
            raise ValueError("Restore source must not be a symbolic link")
        # Validate the managed namespace before strict resolution so an unknown,
        # nonexistent path is rejected as untrusted rather than leaking path errors.
        if not raw_source.name.startswith(self.PREFIX) or not raw_source.name.endswith(self.SUFFIX):
            raise ValueError("Restore source must be a managed backup")
        if raw_source.parent.resolve() != self.root:
            raise ValueError("Restore source must be a managed backup")
        if not raw_source.is_file():
            raise FileNotFoundError(raw_source)
        source = raw_source.resolve(strict=True)
        if not self._is_managed_backup(source):
            raise ValueError("Restore source must be a managed backup")
        target = Path(destination).expanduser().resolve()
        live = Path(self.database.path).expanduser().resolve()
        if self.database.path != ":memory:" and target == live:
            raise ValueError("Restore preview cannot target the live database")
        if target.exists():
            raise FileExistsError("Restore destination already exists")
        if target == source:
            raise ValueError("Restore destination must differ from backup source")
        if not Database.verify_backup(source):
            raise sqlite3.DatabaseError("Restore source failed integrity verification")
        return {
            "preview_only": True, "eligible": True, "source_name": source.name,
            "source_size_bytes": source.stat().st_size, "source_sha256": sha256_file(source),
            "destination_name": target.name, "destination_parent_exists": target.parent.is_dir(),
            "destination_exists": target.exists(), "integrity_verified": True,
            "actions_performed": (),
        }

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
        missing_parent_dirs = []
        parent = target.parent
        while not parent.exists():
            missing_parent_dirs.append(parent)
            parent = parent.parent
        target.parent.mkdir(parents=True, exist_ok=True)
        destination_db = Database(target)
        try:
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
            for directory in missing_parent_dirs:
                try:
                    directory.rmdir()
                except OSError:
                    break
            raise
        finally:
            destination_db.close()

    def restore_drill_idempotent(self, backup_path: str | Path, destination: str | Path) -> Path:
        """Restore once; an identical existing destination is an idempotent no-op."""
        raw_source = Path(backup_path).expanduser()
        raw_target = Path(destination).expanduser()
        if raw_source.is_symlink() or raw_target.is_symlink():
            raise ValueError("Restore source and destination must not be symbolic links")
        source = raw_source.resolve(strict=True)
        target = raw_target.resolve()
        if source.parent != self.root or not source.name.startswith(self.PREFIX) or not source.name.endswith(self.SUFFIX):
            raise ValueError("Restore source must be a managed backup")
        live = Path(self.database.path).expanduser().resolve()
        if self.database.path != ":memory:" and target == live:
            raise ValueError("Idempotent restore cannot target the live database")
        if not Database.verify_backup(source):
            raise sqlite3.DatabaseError("Restore source failed integrity verification")

        if target.exists():
            if not target.is_file() or not Database.verify_backup(target):
                raise FileExistsError("Restore destination exists and is not a verified database")
            if sha256_file(target) != sha256_file(source):
                raise FileExistsError("Restore destination contains different data; no overwrite performed")
            return target

        return self.restore_drill(source, target)
