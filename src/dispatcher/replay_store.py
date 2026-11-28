"""Durable SQLite replay claims for the Phase 20 dispatcher.

The database file must live on persistent storage shared by all dispatcher
workers. Do not use :memory: or ephemeral runner storage in production.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from database.connection import Database


class SQLiteReplayStore:
    """Atomically consume a request ID and nonce in the application SQLite DB."""

    def __init__(self, database: Database) -> None:
        if not isinstance(database, Database):
            raise TypeError("database must be a database.connection.Database")
        self.database = database

    def initialize(self) -> None:
        """Create replay table and indexes idempotently."""
        with self.database.transaction() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS dispatcher_replay_claims (
                    namespace TEXT NOT NULL,
                    value TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    PRIMARY KEY (namespace, value)
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_dispatcher_replay_expiry "
                "ON dispatcher_replay_claims(expires_at)"
            )

    def claim_pair(
        self, request_id: str, nonce: str, expires_at: datetime
    ) -> bool:
        """Atomically claim both values; return False if either was replayed.

        A deliberate exception rolls back the first insert when the second
        collides, preventing partial consumption. Database failures propagate.
        """
        if not isinstance(expires_at, datetime) or expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        expiry = expires_at.astimezone(timezone.utc).isoformat()
        class _DuplicateClaim(Exception):
            pass

        try:
            with self.database.transaction() as connection:
                # Expired claims no longer prevent a valid new request.
                connection.execute(
                    "DELETE FROM dispatcher_replay_claims WHERE expires_at <= ?",
                    (datetime.now(timezone.utc).isoformat(),),
                )
                for namespace, value in (
                    ("request_id", request_id),
                    ("nonce", nonce),
                ):
                    cursor = connection.execute(
                        """INSERT INTO dispatcher_replay_claims
                           (namespace, value, expires_at) VALUES (?, ?, ?)
                           ON CONFLICT(namespace, value) DO NOTHING""",
                        (namespace, value, expiry),
                    )
                    if cursor.rowcount != 1:
                        raise _DuplicateClaim()
        except _DuplicateClaim:
            return False
        return True
