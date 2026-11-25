"""PostgreSQL connection foundation.

The PostgreSQL adapter has separate repository and access-control implementations.
Runtime selection is explicit and production selection remains blocked until
application-service and dashboard acceptance are complete.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Any


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
            raise RuntimeError(
                "PostgreSQL support requires psycopg[binary]>=3.2,<4"
            ) from exc
        return psycopg.connect(
            self.dsn,
            connect_timeout=self.connect_timeout,
            row_factory=dict_row,
            autocommit=True,
        )

    @contextmanager
    def connection(self) -> Iterator[Any]:
        """Yield a dict-row PostgreSQL connection and always close it."""
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        """Commit on success and roll back on any exception."""
        with self.connection() as connection:
            with connection.transaction():
                yield connection

    def health_check(self) -> bool:
        """Check basic connectivity without changing application data."""
        with self.connection() as connection:
            row = connection.execute("SELECT 1 AS ok").fetchone()
            return row is not None and row["ok"] == 1
