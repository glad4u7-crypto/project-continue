"""Small, explicit SQLite connection and transaction manager."""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


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

    def close(self) -> None:
        """Release the anchor connection used by shared in-memory databases."""
        if self._anchor is not None:
            self._anchor.close()
            self._anchor = None
