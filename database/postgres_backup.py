"""Safe PostgreSQL custom-format backup and restore helpers.

These operations are explicit and never run automatically at application startup.
Restore refuses a target containing user objects; it never drops or overwrites a
database. The archive and sidecar manifest are verified before restore.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo


def _tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required PostgreSQL client tool not found: {name}")
    return path


def _connection_parts(dsn: str) -> tuple[str, dict[str, str], dict[str, str]]:
    if not isinstance(dsn, str) or not dsn.strip():
        raise ValueError("PostgreSQL DSN must be a non-empty string")
    params = conninfo_to_dict(dsn.strip())
    password = params.pop("password", None)
    safe_dsn = make_conninfo(**params)
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password
    return safe_dsn, params, env


def _run(command: list[str], env: dict[str, str]) -> str:
    result = subprocess.run(command, env=env, text=True, capture_output=True, check=False)
    if result.returncode:
        detail = (result.stderr or result.stdout or "unknown PostgreSQL client error").strip()
        raise RuntimeError(f"{Path(command[0]).name} failed: {detail}")
    return result.stdout


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_path(archive: Path) -> Path:
    return archive.with_name(archive.name + ".manifest.json")


def _database_is_empty(dsn: str) -> bool:
    with psycopg.connect(dsn) as connection:
        row = connection.execute(
            """SELECT COUNT(*) AS n
                 FROM pg_class c
                 JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                  AND n.nspname NOT LIKE 'pg_toast%'
                  AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')"""
        ).fetchone()
        return row["n"] == 0


def create_postgres_backup(dsn: str, archive_path: str | Path) -> dict[str, Any]:
    """Create and validate a custom-format pg_dump plus SHA-256 manifest."""
    safe_dsn, _params, env = _connection_parts(dsn)
    destination = Path(archive_path).expanduser().resolve()
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing backup: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = _manifest_path(destination)
    if manifest.exists():
        raise FileExistsError(f"Refusing to overwrite existing manifest: {manifest}")

    fd, temporary_name = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp",
                                          dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    temporary.unlink()
    try:
        _run([_tool("pg_dump"), "--format=custom", "--no-owner", "--no-acl",
              "--file", str(temporary), "--dbname", safe_dsn], env)
        _run([_tool("pg_restore"), "--list", str(temporary)], env)
        checksum = _sha256(temporary)
        with psycopg.connect(dsn) as connection:
            server_version = connection.info.server_version
            database_name = connection.info.dbname
        metadata = {
            "format": "postgresql-custom",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "database": database_name,
            "server_version": server_version,
            "archive": destination.name,
            "size_bytes": temporary.stat().st_size,
            "sha256": checksum,
        }
        temporary.replace(destination)
        manifest_tmp = manifest.with_name(manifest.name + ".tmp")
        try:
            manifest_tmp.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
            manifest_tmp.replace(manifest)
        finally:
            manifest_tmp.unlink(missing_ok=True)
        return metadata
    except Exception:
        temporary.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        raise


def verify_postgres_backup(archive_path: str | Path) -> dict[str, Any]:
    """Verify sidecar metadata, byte count, SHA-256 and PostgreSQL archive listing."""
    archive = Path(archive_path).expanduser().resolve()
    manifest = _manifest_path(archive)
    if not archive.is_file() or not manifest.is_file():
        raise FileNotFoundError("Backup archive or its .manifest.json file is missing")
    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    if metadata.get("format") != "postgresql-custom":
        raise ValueError("Unsupported PostgreSQL backup format")
    if metadata.get("archive") != archive.name:
        raise ValueError("Backup manifest archive name does not match")
    if metadata.get("size_bytes") != archive.stat().st_size:
        raise ValueError("Backup archive size does not match manifest")
    if metadata.get("sha256") != _sha256(archive):
        raise ValueError("Backup SHA-256 checksum mismatch")
    _run([_tool("pg_restore"), "--list", str(archive)], os.environ.copy())
    return metadata


def restore_postgres_backup(archive_path: str | Path, target_dsn: str) -> dict[str, Any]:
    """Restore only into an empty target database; never drop or clean target objects."""
    metadata = verify_postgres_backup(archive_path)
    safe_dsn, _params, env = _connection_parts(target_dsn)
    if not _database_is_empty(target_dsn):
        raise RuntimeError("Restore target is not empty; refusing to overwrite existing objects")
    _run([_tool("pg_restore"), "--exit-on-error", "--no-owner", "--no-acl",
          "--dbname", safe_dsn, str(Path(archive_path).expanduser().resolve())], env)
    with psycopg.connect(target_dsn) as connection:
        restored_tables = connection.execute(
            """SELECT COUNT(*) AS n FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')"""
        ).fetchone()["n"]
        schema_version = connection.execute(
            "SELECT version FROM pc_schema_version WHERE id = 1"
        ).fetchone()
    if restored_tables < 1 or schema_version is None:
        raise RuntimeError("Restore verification failed: expected application schema was not found")
    return {
        "restored": True,
        "verified": True,
        "target_schema_version": schema_version["version"],
        "restored_tables": restored_tables,
        "source_backup_sha256": metadata["sha256"],
    }
