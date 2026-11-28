"""SQLite-backed dispatcher admission, queue, concurrency and rate limits."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from database.connection import Database


class AdmissionRejected(RuntimeError):
    """Raised when queue, concurrency or request-rate policy denies admission."""


@dataclass(frozen=True)
class AdmissionLimits:
    max_queued: int = 25
    max_concurrent: int = 3
    actor_rate_limit: int = 30
    global_rate_limit: int = 120
    rate_window_seconds: int = 60
    lease_seconds: int = 900

    def __post_init__(self) -> None:
        for name in (
            "max_queued", "max_concurrent", "actor_rate_limit",
            "global_rate_limit", "rate_window_seconds", "lease_seconds",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.actor_rate_limit > self.global_rate_limit:
            raise ValueError("actor_rate_limit cannot exceed global_rate_limit")


class SQLiteAdmissionController:
    """Persistent admission coordinator; all mutating operations serialize via BEGIN IMMEDIATE.

    Use one durable database shared by all workers. Ephemeral and per-worker
    databases do not provide a global queue or concurrency limit.
    """

    def __init__(self, database: Database, limits: AdmissionLimits | None = None) -> None:
        if not isinstance(database, Database):
            raise TypeError("database must be a Database instance")
        self.database = database
        self.limits = limits or AdmissionLimits()

    def initialize(self) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS dispatcher_admissions (
                    request_id TEXT PRIMARY KEY,
                    actor_id TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('ACK','RUNNING')),
                    admitted_at TEXT NOT NULL,
                    lease_expires_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_dispatcher_admissions_state "
                "ON dispatcher_admissions(state, admitted_at)"
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS dispatcher_rate_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    UNIQUE(request_id)
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_dispatcher_rate_actor_time "
                "ON dispatcher_rate_events(actor_id, occurred_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_dispatcher_rate_time "
                "ON dispatcher_rate_events(occurred_at)"
            )

    @staticmethod
    def _timestamp(value: datetime) -> str:
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat()

    def _begin(self):
        connection = self.database.connection()
        raw = connection.__enter__()
        raw.execute("BEGIN IMMEDIATE")
        return connection, raw

    @staticmethod
    def _commit(manager: Any, connection: Any) -> None:
        # Database.connection() closes its connection on context exit but does
        # not commit explicit transactions. Commit the SQLite transaction first.
        connection.commit()
        manager.__exit__(None, None, None)

    @staticmethod
    def _rollback(manager: Any, connection: Any, exc: BaseException) -> None:
        connection.rollback()
        manager.__exit__(type(exc), exc, exc.__traceback__)

    def _purge(self, connection: Any, now_text: str, cutoff_text: str) -> None:
        connection.execute("DELETE FROM dispatcher_admissions WHERE lease_expires_at <= ?", (now_text,))
        connection.execute("DELETE FROM dispatcher_rate_events WHERE occurred_at <= ?", (cutoff_text,))

    def admit(self, request_id: str, actor_id: str, *, now: datetime | None = None) -> None:
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("request_id must be non-empty")
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise ValueError("actor_id must be non-empty")
        current = now or datetime.now(timezone.utc)
        now_text = self._timestamp(current)
        cutoff_text = self._timestamp(current - timedelta(seconds=self.limits.rate_window_seconds))
        expiry_text = self._timestamp(current + timedelta(seconds=self.limits.lease_seconds))
        manager, connection = self._begin()
        try:
            self._purge(connection, now_text, cutoff_text)
            queued = connection.execute(
                "SELECT COUNT(*) FROM dispatcher_admissions WHERE state='ACK'"
            ).fetchone()[0]
            if queued >= self.limits.max_queued:
                raise AdmissionRejected("queue capacity reached")
            actor_count = connection.execute(
                "SELECT COUNT(*) FROM dispatcher_rate_events WHERE actor_id=? AND occurred_at>?",
                (actor_id, cutoff_text),
            ).fetchone()[0]
            if actor_count >= self.limits.actor_rate_limit:
                raise AdmissionRejected("actor request rate limit exceeded")
            global_count = connection.execute(
                "SELECT COUNT(*) FROM dispatcher_rate_events WHERE occurred_at>?",
                (cutoff_text,),
            ).fetchone()[0]
            if global_count >= self.limits.global_rate_limit:
                raise AdmissionRejected("global request rate limit exceeded")
            connection.execute(
                "INSERT INTO dispatcher_admissions VALUES (?, ?, 'ACK', ?, ?)",
                (request_id, actor_id, now_text, expiry_text),
            )
            connection.execute(
                "INSERT INTO dispatcher_rate_events(request_id, actor_id, occurred_at) VALUES (?, ?, ?)",
                (request_id, actor_id, now_text),
            )
            self._commit(manager, connection)
        except BaseException as exc:
            self._rollback(manager, connection, exc)
            if isinstance(exc, sqlite3.IntegrityError):
                raise AdmissionRejected("duplicate request admission") from exc
            raise

    def start(self, request_id: str, *, now: datetime | None = None) -> None:
        current = now or datetime.now(timezone.utc)
        now_text = self._timestamp(current)
        manager, connection = self._begin()
        try:
            connection.execute(
                "DELETE FROM dispatcher_admissions WHERE lease_expires_at <= ?", (now_text,)
            )
            active = connection.execute(
                "SELECT COUNT(*) FROM dispatcher_admissions WHERE state='RUNNING'"
            ).fetchone()[0]
            if active >= self.limits.max_concurrent:
                raise AdmissionRejected("concurrency capacity reached")
            cursor = connection.execute(
                "UPDATE dispatcher_admissions SET state='RUNNING', lease_expires_at=? "
                "WHERE request_id=? AND state='ACK' AND lease_expires_at>?",
                (self._timestamp(current + timedelta(seconds=self.limits.lease_seconds)),
                 request_id, now_text),
            )
            if cursor.rowcount != 1:
                raise AdmissionRejected("request is missing, expired or not queued")
            self._commit(manager, connection)
        except BaseException as exc:
            self._rollback(manager, connection, exc)
            raise

    def release(self, request_id: str) -> bool:
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("request_id must be non-empty")
        manager, connection = self._begin()
        try:
            cursor = connection.execute(
                "DELETE FROM dispatcher_admissions WHERE request_id=?", (request_id,)
            )
            self._commit(manager, connection)
            return cursor.rowcount == 1
        except BaseException as exc:
            self._rollback(manager, connection, exc)
            raise

    def snapshot(self, *, now: datetime | None = None) -> dict[str, int]:
        current = now or datetime.now(timezone.utc)
        now_text = self._timestamp(current)
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM dispatcher_admissions WHERE lease_expires_at <= ?", (now_text,)
            )
            row = connection.execute(
                "SELECT SUM(CASE WHEN state='ACK' THEN 1 ELSE 0 END) AS queued, "
                "SUM(CASE WHEN state='RUNNING' THEN 1 ELSE 0 END) AS running "
                "FROM dispatcher_admissions"
            ).fetchone()
        return {"queued": int(row["queued"] or 0), "running": int(row["running"] or 0)}
