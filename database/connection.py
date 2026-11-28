"""Small, explicit SQLite connection, transaction and backup manager."""

from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from urllib.parse import quote


class Database:
    """Create short-lived SQLite connections with safe defaults.

    The database path is injected by the caller so tests and applications can
    choose isolated storage locations. The :memory: mode uses a private shared
    in-memory URI held alive by an anchor connection.
    """

    def __init__(self, path: str | Path, *, timeout: float = 5.0) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        self.path = str(path)
        self.timeout = float(timeout)
        self._use_uri = self.path == ":memory:"
        self._dsn = (
            f"file:project_continue_{uuid.uuid4().hex}?mode=memory&cache=shared"
            if self._use_uri else self.path
        )
        self._anchor: sqlite3.Connection | None = None
        if self._use_uri:
            self._anchor = sqlite3.connect(
                self._dsn,
                uri=True,
                timeout=self.timeout,
                isolation_level=None,
            )
            self._configure(self._anchor)

    def _prepare_path(self) -> None:
        if not self._use_uri:
            Path(self.path).expanduser().parent.mkdir(parents=True, exist_ok=True)

    def _configure(self, connection: sqlite3.Connection) -> None:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {int(self.timeout * 1000)}")

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a configured connection and always close it afterwards."""
        self._prepare_path()
        connection = sqlite3.connect(
            self._dsn,
            uri=self._use_uri,
            timeout=self.timeout,
            isolation_level=None,
        )
        self._configure(connection)
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run an explicit transaction, committing or rolling back atomically."""
        with self.connection() as connection:
            connection.execute("BEGIN")
            try:
                yield connection
            except BaseException:
                connection.rollback()
                raise
            else:
                connection.commit()

    def health_check(self) -> bool:
        """Return true when SQLite can execute a trivial query."""
        with self.connection() as connection:
            row = connection.execute("SELECT 1 AS ok").fetchone()
            return row is not None and row["ok"] == 1

    def backup(self, destination: str | Path) -> Path:
        """Create a new, integrity-checked backup without overwriting any file.

        The backup is created with owner-only permissions where supported.
        Existing destinations are rejected to avoid accidental data loss.
        """
        raw_destination = str(destination)
        if not raw_destination.strip():
            raise ValueError("backup destination must not be empty")
        target = Path(raw_destination).expanduser()
        if not self._use_uri and Path(self.path).expanduser().resolve() == target.resolve():
            raise ValueError("backup destination must differ from the source database")
        target.parent.mkdir(parents=True, exist_ok=True)

        descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        try:
            with self.connection() as source:
                backup_connection = sqlite3.connect(str(target), timeout=self.timeout)
                try:
                    source.backup(backup_connection)
                    result = backup_connection.execute("PRAGMA integrity_check").fetchone()
                    if result is None or result[0] != "ok":
                        raise sqlite3.DatabaseError("SQLite backup integrity check failed")
                finally:
                    backup_connection.close()
            os.chmod(target, 0o600)
            return target
        except BaseException:
            target.unlink(missing_ok=True)
            raise

    @staticmethod
    def verify_backup(path: str | Path) -> bool:
        """Verify SQLite integrity and foreign-key consistency in read-only mode."""
        target = Path(path).expanduser()
        if target.is_symlink():
            raise ValueError("Backup must not be a symbolic link")
        if not target.is_file():
            raise FileNotFoundError(target)
        uri = f"file:{quote(str(target.resolve()), safe='/:')}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
            return integrity is not None and integrity[0] == "ok" and not foreign_key_errors
        finally:
            connection.close()

    def close(self) -> None:
        """Release the anchor connection used by shared in-memory databases."""
        if self._anchor is not None:
            self._anchor.close()
            self._anchor = None
