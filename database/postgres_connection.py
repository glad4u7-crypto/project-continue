"""PostgreSQL connection foundation with the SQLite service SQL compatibility shim."""
from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

class _PostgresServiceConnection:
    """Expose the small SQLite connection surface used by existing services."""
    def __init__(self, connection: Any, integrity_error: type[BaseException]) -> None:
        self._connection = connection
        self._integrity_error = integrity_error

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)

    @staticmethod
    def _sql(statement: str) -> str:
        # Existing services use '?' bind markers; repository SQL uses '%s'.
        return statement.replace("?", "%s")

    def execute(self, statement: str, parameters: Any = ()) -> Any:
        try:
            return self._connection.execute(self._sql(statement), parameters)
        except self._integrity_error as exc:
            raise sqlite3.IntegrityError(str(exc)) from exc

    def executemany(self, statement: str, parameters: Any) -> Any:
        try:
            return self._connection.executemany(self._sql(statement), parameters)
        except self._integrity_error as exc:
            raise sqlite3.IntegrityError(str(exc)) from exc

    def executescript(self, script: str) -> None:
        """Execute the simple semicolon-delimited DDL scripts used by services."""
        for statement in script.split(";"):
            if statement.strip():
                self.execute(statement)

class PostgresDatabase:
    """Short-lived PostgreSQL connections using psycopg 3 and dict rows."""
    def __init__(self, dsn: str, *, connect_timeout: int = 10) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("PostgreSQL DSN must be a non-empty string")
        if connect_timeout < 1 or connect_timeout > 60:
            raise ValueError("connect_timeout must be between 1 and 60 seconds")
        self.dsn = dsn.strip()
        self.connect_timeout = connect_timeout

    def _connect(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("PostgreSQL support requires psycopg[binary]>=3.2,<4") from exc
        connection = psycopg.connect(
            self.dsn, connect_timeout=self.connect_timeout,
            row_factory=dict_row, autocommit=True,
        )
        return connection, psycopg.IntegrityError

    @contextmanager
    def connection(self) -> Iterator[_PostgresServiceConnection]:
        raw, integrity_error = self._connect()
        try:
            yield _PostgresServiceConnection(raw, integrity_error)
        finally:
            raw.close()

    @contextmanager
    def transaction(self) -> Iterator[_PostgresServiceConnection]:
        with self.connection() as connection:
            with connection.transaction():
                yield connection

    def health_check(self) -> bool:
        with self.connection() as connection:
            row = connection.execute("SELECT 1 AS ok").fetchone()
            return row is not None and row["ok"] == 1
