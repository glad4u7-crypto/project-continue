"""Create, inventory and preview SQLite backups without performing restores."""
from __future__ import annotations

import hashlib
import hmac
import re
import sqlite3
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from database.connection import Database
from database.diagnostics import SQLiteIntegrityReport, inspect_sqlite_database

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_HASH_CHUNK_BYTES = 1024 * 1024
_ALLOWED_BACKUP_SUFFIXES = frozenset({".db", ".sqlite", ".sqlite3"})
MAX_BACKUP_INVENTORY_ENTRIES = 500


@dataclass(frozen=True)
class BackupManifest:
    """Minimal backup identity and verification evidence."""

    path: Path
    size_bytes: int
    sha256: str
    integrity_verified: bool


@dataclass(frozen=True)
class BackupInventoryItem:
    """Metadata-only inventory record for one regular backup file."""

    name: str
    size_bytes: int
    sha256: str
    modified_at_utc: str
    integrity_report: SQLiteIntegrityReport | None
    inspection_error: str | None


@dataclass(frozen=True)
class BackupRestorePreview:
    """Read-only restore eligibility assessment; it never restores a file."""

    name: str
    size_bytes: int
    sha256: str
    checksum_matches: bool
    integrity_report: SQLiteIntegrityReport | None
    eligible_for_manual_restore_review: bool
    reason: str
    restore_performed: bool = False


def sha256_file(path: str | Path) -> str:
    """Hash a regular file incrementally without loading it all into memory."""
    target = Path(path).expanduser()
    if not target.is_file():
        raise FileNotFoundError(target)
    digest = hashlib.sha256()
    with target.open("rb") as stream:
        for chunk in iter(lambda: stream.read(_HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_backup_checksum(path: str | Path, expected_sha256: str) -> bool:
    """Compare a backup's SHA-256 with a strict, caller-supplied digest."""
    if not isinstance(expected_sha256, str) or not _SHA256_RE.fullmatch(expected_sha256):
        raise ValueError("expected_sha256 must be 64 lowercase hexadecimal characters")
    actual = sha256_file(path)
    return hmac.compare_digest(actual, expected_sha256)


def create_verified_backup(database: Database, destination: str | Path) -> BackupManifest:
    """Create a no-overwrite SQLite backup, verify DB integrity, then hash it."""
    if not isinstance(database, Database):
        raise TypeError("database must be a Database instance")
    backup_path = database.backup(destination)
    if not Database.verify_backup(backup_path):
        raise RuntimeError("created backup failed SQLite integrity or foreign-key verification")
    digest = sha256_file(backup_path)
    return BackupManifest(
        path=backup_path,
        size_bytes=backup_path.stat().st_size,
        sha256=digest,
        integrity_verified=True,
    )


def inventory_backups(directory: str | Path) -> tuple[BackupInventoryItem, ...]:
    """Inventory immediate regular backup files; skip symlinks and never mutate."""
    root = Path(directory).expanduser()
    if root.is_symlink():
        raise ValueError("backup inventory directory must not be a symlink")
    if not root.is_dir():
        raise FileNotFoundError(root)

    candidates = []
    for candidate in sorted(root.iterdir(), key=lambda item: item.name):
        if candidate.is_symlink() or candidate.suffix.lower() not in _ALLOWED_BACKUP_SUFFIXES:
            continue
        metadata = candidate.stat(follow_symlinks=False)
        if not stat.S_ISREG(metadata.st_mode):
            continue
        candidates.append((candidate, metadata))
        if len(candidates) > MAX_BACKUP_INVENTORY_ENTRIES:
            raise ValueError("backup inventory exceeds the 500-file safety limit")

    results = []
    for candidate, metadata in candidates:
        digest = sha256_file(candidate)
        inspection = None
        inspection_error = None
        try:
            inspection = inspect_sqlite_database(candidate)
        except (sqlite3.DatabaseError, OSError):
            inspection_error = "sqlite_inspection_failed"
        results.append(
            BackupInventoryItem(
                name=candidate.name,
                size_bytes=metadata.st_size,
                sha256=digest,
                modified_at_utc=datetime.fromtimestamp(
                    metadata.st_mtime, tz=timezone.utc
                ).isoformat(),
                integrity_report=inspection,
                inspection_error=inspection_error,
            )
        )
    return tuple(results)


def preview_backup_restore(
    path: str | Path,
    expected_sha256: str,
) -> BackupRestorePreview:
    """Check a backup's checksum/schema/integrity without selecting a target."""
    target = Path(path).expanduser()
    if target.is_symlink():
        raise ValueError("restore preview does not follow symlinks")
    if not target.is_file():
        raise FileNotFoundError(target)

    if not isinstance(expected_sha256, str) or not _SHA256_RE.fullmatch(expected_sha256):
        raise ValueError("expected_sha256 must be 64 lowercase hexadecimal characters")

    metadata = target.stat(follow_symlinks=False)
    digest = sha256_file(target)
    checksum_matches = hmac.compare_digest(digest, expected_sha256)
    if not checksum_matches:
        return BackupRestorePreview(
            name=target.name,
            size_bytes=metadata.st_size,
            sha256=digest,
            checksum_matches=False,
            integrity_report=None,
            eligible_for_manual_restore_review=False,
            reason="checksum_mismatch",
        )

    try:
        report = inspect_sqlite_database(target)
    except (sqlite3.DatabaseError, OSError):
        return BackupRestorePreview(
            name=target.name,
            size_bytes=metadata.st_size,
            sha256=digest,
            checksum_matches=True,
            integrity_report=None,
            eligible_for_manual_restore_review=False,
            reason="sqlite_inspection_failed",
        )

    if not report.schema_version_supported:
        reason = "schema_version_unsupported"
    elif report.integrity_results != ("ok",):
        reason = "integrity_check_failed"
    elif report.foreign_key_violations:
        reason = "foreign_key_check_failed"
    else:
        reason = "verified_preview_only"

    return BackupRestorePreview(
        name=target.name,
        size_bytes=metadata.st_size,
        sha256=digest,
        checksum_matches=True,
        integrity_report=report,
        eligible_for_manual_restore_review=reason == "verified_preview_only",
        reason=reason,
    )
