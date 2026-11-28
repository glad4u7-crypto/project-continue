"""Create SQLite backups with independently verifiable SHA-256 manifests."""
from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from pathlib import Path

from database.connection import Database

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_HASH_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True)
class BackupManifest:
    """Minimal backup identity and verification evidence."""

    path: Path
    size_bytes: int
    sha256: str
    integrity_verified: bool


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
