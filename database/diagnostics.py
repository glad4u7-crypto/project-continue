"""Read-only SQLite schema and integrity diagnostics."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from database.schema import SCHEMA_VERSION


@dataclass(frozen=True)
class ForeignKeyViolation:
    """One row returned by SQLite PRAGMA foreign_key_check."""

    table: str
    rowid: int | None
    parent_table: str
    foreign_key_index: int


@dataclass(frozen=True)
class SQLiteIntegrityReport:
    """Non-mutating database health result; no application records are included."""

    schema_version: int | None
    expected_schema_version: int
    integrity_results: tuple[str, ...]
    foreign_key_violations: tuple[ForeignKeyViolation, ...]

    @property
    def schema_version_supported(self) -> bool:
        return self.schema_version == self.expected_schema_version

    @property
    def healthy(self) -> bool:
        return (
            self.schema_version_supported
            and self.integrity_results == ("ok",)
            and not self.foreign_key_violations
        )


def inspect_sqlite_database(path: str | Path) -> SQLiteIntegrityReport:
    """Inspect schema version and SQLite integrity using a read-only connection.

    The function never creates a missing file and never applies migrations.
    """
    target = Path(path).expanduser()
    if not target.is_file():
        raise FileNotFoundError(target)
    resolved = target.resolve(strict=True)
    uri = f"file:{quote(str(resolved), safe='/:')}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5.0)
    try:
        schema_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_version'"
        ).fetchone()
        schema_version = None
        if schema_table is not None:
            row = connection.execute(
                "SELECT version FROM schema_version WHERE id = 1"
            ).fetchone()
            if row is not None and isinstance(row[0], int) and not isinstance(row[0], bool):
                schema_version = row[0]

        integrity_results = tuple(
            str(row[0]) for row in connection.execute("PRAGMA integrity_check").fetchall()
        )
        foreign_key_violations = tuple(
            ForeignKeyViolation(
                table=str(row[0]),
                rowid=row[1] if isinstance(row[1], int) else None,
                parent_table=str(row[2]),
                foreign_key_index=int(row[3]),
            )
            for row in connection.execute("PRAGMA foreign_key_check").fetchall()
        )
        return SQLiteIntegrityReport(
            schema_version=schema_version,
            expected_schema_version=SCHEMA_VERSION,
            integrity_results=integrity_results,
            foreign_key_violations=foreign_key_violations,
        )
    finally:
        connection.close()
