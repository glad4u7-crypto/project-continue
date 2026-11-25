"""Explicit, transactional SQLite-to-PostgreSQL migration utility.

The default operation is a read-only dry run. A real migration requires an
explicit dry_run=False call and a dedicated, empty PostgreSQL target database.
The application runtime never invokes this module automatically.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import quote

from database.postgres_connection import PostgresDatabase
from database.postgres_schema import POSTGRES_SCHEMA_VERSION, initialize_postgres_schema
from database.schema import SCHEMA_VERSION


_TABLES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "projects": (("id", "name", "description", "status", "created_at", "updated_at"), ("id",)),
    "tasks": (("id", "project_id", "title", "description", "assignee", "priority",
               "status", "due_at", "created_at", "updated_at"), ("id",)),
    "pc_users": (("id", "email", "password_salt", "password_hash", "role", "enabled",
                  "created_at"), ("id",)),
    "pc_project_memberships": (("project_id", "user_id", "role", "created_at"),
                               ("project_id", "user_id")),
    "task_dependencies": (("task_id", "depends_on_task_id", "created_at"),
                          ("task_id", "depends_on_task_id")),
    "activity_history": (("id", "project_id", "task_id", "event_type", "payload_json",
                          "created_at"), ("id",)),
    "pc_audit_events": (("id", "actor_id", "action", "project_id", "outcome",
                         "created_at"), ("id",)),
    "pc_login_attempts": (("email_digest", "attempted_at", "succeeded"),
                          ("email_digest", "attempted_at", "succeeded")),
}


def _json_value(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"__bytes_hex__": bytes(value).hex()}
    return value


def _checksum(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        encoded = json.dumps(
            {key: _json_value(value) for key, value in row.items()},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")
        digest.update(encoded)
        digest.update(b"\n")
    return digest.hexdigest()


def _open_sqlite_readonly(path: str | Path) -> sqlite3.Connection:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    uri = f"file:{quote(str(source), safe='/:')}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def _source_snapshot(connection: sqlite3.Connection) -> tuple[int, dict[str, list[dict[str, Any]]]]:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()
    if integrity is None or integrity[0] != "ok":
        raise RuntimeError("SQLite integrity_check failed")
    foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_errors:
        raise RuntimeError(f"SQLite foreign_key_check failed: {len(foreign_key_errors)} violation(s)")

    tables = {row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    if "schema_version" not in tables:
        raise RuntimeError("SQLite schema_version table is missing")
    version_row = connection.execute(
        "SELECT version FROM schema_version WHERE id=1"
    ).fetchone()
    if version_row is None:
        raise RuntimeError("SQLite schema version row is missing")
    source_version = int(version_row["version"])
    if source_version != SCHEMA_VERSION:
        raise RuntimeError(
            f"Expected SQLite schema version {SCHEMA_VERSION}, found {source_version}; "
            "upgrade/verify the source database before migration"
        )

    snapshot: dict[str, list[dict[str, Any]]] = {}
    for table, (columns, order_by) in _TABLES.items():
        if table not in tables:
            snapshot[table] = []
            continue
        selected = ", ".join(columns)
        ordering = ", ".join(order_by)
        rows = connection.execute(
            f"SELECT {selected} FROM {table} ORDER BY {ordering}"
        ).fetchall()
        snapshot[table] = [dict(row) for row in rows]
    return source_version, snapshot


def migrate_sqlite_to_postgres(
    sqlite_path: str | Path,
    postgres_dsn: str,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Audit or migrate a SQLite database into an empty PostgreSQL database.

    Dry-run reads and validates only the SQLite source. A real migration first
    initializes the PostgreSQL schema, then inserts and verifies every row in
    one PostgreSQL transaction. Any insert/count/checksum failure rolls back
    all migrated application rows.
    """
    if not isinstance(dry_run, bool):
        raise TypeError("dry_run must be a bool")

    source = _open_sqlite_readonly(sqlite_path)
    try:
        source_version, snapshot = _source_snapshot(source)
    finally:
        source.close()

    source_report = {
        table: {"rows": len(rows), "sha256": _checksum(rows)}
        for table, rows in snapshot.items()
    }
    report: dict[str, Any] = {
        "dry_run": dry_run,
        "source_schema_version": source_version,
        "target_schema_version": POSTGRES_SCHEMA_VERSION,
        "tables": source_report,
    }
    if dry_run:
        return report

    if POSTGRES_SCHEMA_VERSION != source_version:
        raise RuntimeError(
            "SQLite and PostgreSQL schema versions differ; refusing migration"
        )

    database = PostgresDatabase(postgres_dsn)
    initialize_postgres_schema(database)

    with database.transaction() as target:
        for table in _TABLES:
            count = target.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
            if count:
                raise RuntimeError(
                    f"PostgreSQL target table {table} is not empty; refusing to merge datasets"
                )

        for table, (columns, _order_by) in _TABLES.items():
            rows = snapshot[table]
            if not rows:
                continue
            column_sql = ", ".join(columns)
            placeholders = ", ".join(["%s"] * len(columns))
            insert_sql = f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})"
            for row in rows:
                target.execute(insert_sql, tuple(row[column] for column in columns))

        target.execute(
            "UPDATE pc_schema_version SET version = %s WHERE id = 1",
            (POSTGRES_SCHEMA_VERSION,),
        )

        # Explicitly copied identity values must advance their PostgreSQL sequences.
        for table in ("activity_history", "pc_audit_events"):
            target.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"GREATEST(COALESCE(MAX(id), 1), 1), MAX(id) IS NOT NULL) FROM {table}"
            )

        for table, (columns, order_by) in _TABLES.items():
            column_sql = ", ".join(columns)
            ordering = ", ".join(order_by)
            rows = [dict(row) for row in target.execute(
                f"SELECT {column_sql} FROM {table} ORDER BY {ordering}"
            ).fetchall()]
            expected = source_report[table]
            actual = {"rows": len(rows), "sha256": _checksum(rows)}
            if actual != expected:
                raise RuntimeError(
                    f"PostgreSQL verification failed for {table}: "
                    f"expected {expected}, got {actual}"
                )

    report["migrated"] = True
    report["verified"] = True
    return report
