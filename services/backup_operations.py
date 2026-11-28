"""Safe SQLite backup inventory, preview and isolated restore operations."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

from database.connection import Database
from database.schema import SCHEMA_VERSION

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class BackupOperations:
    """Verified backups; restore drills never target or overwrite the live DB."""

    PREFIX = "project-continue-"
    SUFFIX = ".sqlite3"

    def __init__(self, database: Database, backup_root: str | Path, *, clock=None):
        self.database = database
        candidate = Path(backup_root).expanduser()
        absolute_candidate = Path(os.path.abspath(candidate))
        if any(part.is_symlink() for part in (absolute_candidate, *absolute_candidate.parents)):
            raise ValueError("Backup directory path must not contain symbolic links")
        self.root = absolute_candidate.resolve()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        source = Path(database.path).expanduser().resolve()
        if database.path != ":memory:" and self.root == source.parent:
            raise ValueError("Backup directory must differ from the live database directory")
        self._retention_previews: dict[str, list[dict]] = {}

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _manifest_path(backup: Path) -> Path:
        return backup.with_name(backup.name + ".manifest.json")

    def _managed_backup(self, value: str | Path) -> Path:
        raw = Path(value).expanduser()
        if raw.is_symlink():
            raise ValueError("Backup source must not be a symbolic link")
        source = raw.resolve(strict=True)
        if (source.parent != self.root or not source.is_file()
                or not source.name.startswith(self.PREFIX)
                or not source.name.endswith(self.SUFFIX)):
            raise ValueError("Backup source must be a managed backup")
        return source

    @staticmethod
    def inspect_sqlite(path: str | Path) -> dict:
        target = Path(path).expanduser()
        if target.is_symlink() or not target.is_file():
            raise ValueError("SQLite backup must be a regular non-symlink file")
        uri = f"file:{quote(str(target.resolve()), safe='/:')}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            fk_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
            tables = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            if "schema_version" not in tables:
                raise ValueError("Database schema_version table is missing")
            version_row = connection.execute(
                "SELECT version FROM schema_version WHERE id=1"
            ).fetchone()
            if version_row is None:
                raise ValueError("Database schema version row is missing")
            version = int(version_row[0])
            if version != SCHEMA_VERSION:
                raise ValueError("Database schema version does not match this application")
            if integrity is None or integrity[0] != "ok" or fk_errors:
                raise ValueError("SQLite integrity_check or foreign_key_check failed")
            return {
                "integrity_check": "ok",
                "foreign_key_check": "ok",
                "schema_version": version,
            }
        finally:
            connection.close()

    def create_backup(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        stamp = self.clock().astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        target = self.root / f"{self.PREFIX}{stamp}{self.SUFFIX}"
        created = self.database.backup(target)
        manifest = self._manifest_path(created)
        try:
            inspection = self.inspect_sqlite(created)
            record = {
                "format": "project-continue-sqlite-v1",
                "archive": created.name,
                "size_bytes": created.stat().st_size,
                "sha256": self._sha256(created),
                "created_at": self.clock().astimezone(timezone.utc).isoformat(),
                **inspection,
            }
            payload = (json.dumps(record, sort_keys=True, indent=2) + "\n").encode("utf-8")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(manifest, flags, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(manifest, 0o600)
            if not self.verify_backup(created):
                raise sqlite3.DatabaseError("Backup manifest/checksum verification failed")
            return created
        except BaseException:
            manifest.unlink(missing_ok=True)
            created.unlink(missing_ok=True)
            raise

    def verify_backup(self, backup_path: str | Path) -> dict:
        backup = self._managed_backup(backup_path)
        manifest = self._manifest_path(backup)
        if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > 16 * 1024:
            raise ValueError("Backup manifest is missing or unsafe")
        try:
            record = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("Backup manifest is malformed") from exc
        if not isinstance(record, dict) or record.get("format") != "project-continue-sqlite-v1":
            raise ValueError("Backup manifest format is unsupported")
        if record.get("archive") != backup.name:
            raise ValueError("Backup manifest archive identity mismatch")
        if record.get("size_bytes") != backup.stat().st_size:
            raise ValueError("Backup size does not match manifest")
        digest = self._sha256(backup)
        if not _SHA256.fullmatch(str(record.get("sha256", ""))) or digest != record["sha256"]:
            raise ValueError("Backup SHA-256 does not match manifest")
        inspection = self.inspect_sqlite(backup)
        for key, value in inspection.items():
            if record.get(key) != value:
                raise ValueError("Backup schema/integrity metadata mismatch")
        return {**record, "verified": True}

    def inventory_backups(self) -> dict:
        items = []
        if not self.root.exists():
            return {"items": [], "count": 0}
        for item in sorted(self.root.iterdir(), key=lambda p: p.name):
            if item.is_symlink() or not item.is_file():
                continue
            if not item.name.startswith(self.PREFIX) or not item.name.endswith(self.SUFFIX):
                continue
            try:
                verified = self.verify_backup(item)
                items.append({
                    "name": item.name, "size_bytes": item.stat().st_size,
                    "sha256": verified["sha256"], "schema_version": verified["schema_version"],
                    "status": "verified",
                })
            except (OSError, ValueError, sqlite3.DatabaseError):
                items.append({
                    "name": item.name, "size_bytes": item.stat().st_size,
                    "sha256": None, "schema_version": None, "status": "invalid",
                })
        return {"items": items, "count": len(items)}

    def preview_restore(self, backup_path: str | Path, destination: str | Path) -> dict:
        backup = self._managed_backup(backup_path)
        verified = self.verify_backup(backup)
        raw_target = Path(destination).expanduser()
        absolute_target = Path(os.path.abspath(raw_target))
        if any(part.is_symlink() for part in (absolute_target, *absolute_target.parents)):
            raise ValueError("Restore destination path must not contain symbolic links")
        target = absolute_target.resolve()
        live = Path(self.database.path).expanduser().resolve()
        if self.database.path != ":memory:" and target == live:
            raise ValueError("Restore drill cannot overwrite the live database")
        if target.exists():
            raise FileExistsError("Restore destination already exists")
        if target == backup:
            raise ValueError("Restore destination must differ from backup source")
        return {
            "status": "PREVIEW_ONLY", "source": backup.name,
            "source_sha256": verified["sha256"], "schema_version": verified["schema_version"],
            "destination": str(target), "would_create": True, "writes_performed": False,
        }

    def restore_drill(self, backup_path: str | Path, destination: str | Path) -> Path:
        preview = self.preview_restore(backup_path, destination)
        source = self._managed_backup(backup_path)
        target = Path(preview["destination"])
        target.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(target, flags, 0o600)
        os.close(descriptor)
        destination_db = Database(target)
        try:
            source_uri = f"file:{quote(str(source), safe='/:')}?mode=ro"
            with sqlite3.connect(source_uri, uri=True) as src:
                with destination_db.connection() as dst:
                    src.backup(dst)
            self.inspect_sqlite(target)
            os.chmod(target, 0o600)
            return target
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        finally:
            destination_db.close()

    def preview_retention(self, *, keep_days=30) -> dict:
        if isinstance(keep_days, bool) or not isinstance(keep_days, int) or not 1 <= keep_days <= 3650:
            raise ValueError("keep_days must be between 1 and 3650")
        cutoff = self.clock().astimezone(timezone.utc) - timedelta(days=keep_days)
        candidates = []
        if self.root.exists():
            for item in self.root.iterdir():
                if (item.is_file() and not item.is_symlink()
                        and item.name.startswith(self.PREFIX) and item.name.endswith(self.SUFFIX)):
                    try:
                        verified = self.verify_backup(item)
                    except (OSError, ValueError, sqlite3.DatabaseError):
                        continue
                    stat_result = item.stat()
                    if datetime.fromtimestamp(stat_result.st_mtime, timezone.utc) < cutoff:
                        candidates.append({
                            "name": item.name, "sha256": verified["sha256"],
                            "size_bytes": stat_result.st_size, "mtime_ns": stat_result.st_mtime_ns,
                        })
        preview_id = uuid.uuid4().hex
        self._retention_previews[preview_id] = candidates
        return {
            "preview_id": preview_id, "keep_days": keep_days,
            "cutoff": cutoff.isoformat(), "candidate_count": len(candidates),
            "candidates": candidates, "writes_performed": False,
        }

    def apply_retention(self, preview: dict, *, confirm=False, approval_id: str | None = None) -> list[str]:
        if confirm is not True or not isinstance(approval_id, str) or not approval_id.strip():
            raise PermissionError("Explicit confirmation and approval_id are required for backup deletion")
        if not isinstance(preview, dict) or not isinstance(preview.get("preview_id"), str):
            raise ValueError("A valid retention preview is required")
        expected = self._retention_previews.pop(preview["preview_id"], None)
        if expected is None or preview.get("candidates") != expected:
            raise ValueError("Retention preview is unknown, stale or modified")
        deleted = []
        for item in expected:
            path = self.root / item["name"]
            if path.is_symlink() or not path.is_file():
                raise ValueError("Retention candidate changed after preview")
            stat_result = path.stat()
            if (stat_result.st_size != item["size_bytes"]
                    or stat_result.st_mtime_ns != item["mtime_ns"]
                    or self._sha256(path) != item["sha256"]):
                raise ValueError("Retention candidate changed after preview")
            manifest = self._manifest_path(path)
            if manifest.is_symlink() or not manifest.is_file():
                raise ValueError("Retention manifest changed after preview")
            path.unlink()
            manifest.unlink()
            deleted.append(str(path))
        return deleted

    def authorize_destructive_operation(
        self, operation: str, target: str | Path, *, approval_id: str,
        expected_sha256: str,
    ) -> dict:
        """Validate an explicit approval binding; deliberately performs no mutation."""
        if operation not in {"restore_live", "delete_backup", "overwrite_database"}:
            raise ValueError("Unsupported destructive operation")
        if not isinstance(approval_id, str) or not approval_id.strip() or len(approval_id) > 128:
            raise PermissionError("Explicit approval_id is required")
        raw = Path(target).expanduser()
        if raw.is_symlink() or not raw.is_file():
            raise PermissionError("Destructive target must be an existing regular file")
        actual = self._sha256(raw)
        if not _SHA256.fullmatch(expected_sha256 or "") or actual != expected_sha256:
            raise PermissionError("Destructive target SHA-256 changed or does not match approval")
        if operation == "delete_backup":
            self._managed_backup(raw)
        elif operation in {"restore_live", "overwrite_database"}:
            live = Path(self.database.path).expanduser().resolve()
            if self.database.path == ":memory:" or raw.resolve() != live:
                raise PermissionError("Live restore/overwrite approval must name the exact configured database")
        return {
            "authorized": True, "operation": operation,
            "target": str(raw.resolve()), "sha256": actual,
            "approval_id": approval_id.strip(), "mutation_performed": False,
        }
