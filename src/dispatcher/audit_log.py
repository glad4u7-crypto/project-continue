"""Append-only, privacy-minimized audit events correlated by dispatcher request ID."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


_ALLOWED_TYPES = {
    "request.accepted", "execution.started", "execution.passed",
    "execution.failed", "execution.blocked", "execution.cancelled",
}


class AuditEventRejected(ValueError):
    """Raised when an audit event is malformed or cannot be safely appended."""


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    request_id: str
    event_type: str
    actor_id: str
    repository_id: int
    task_id: str
    state: str
    occurred_at: datetime


class SQLiteAuditLog:
    """Durable append-only audit log; stores identifiers, never task arguments/secrets."""

    def __init__(self, database: Any) -> None:
        if not callable(getattr(database, "connection", None)):
            raise TypeError("database must provide connection()")
        self._database = database

    def initialize(self) -> None:
        with self._database.connection() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS dispatcher_audit_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    request_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    repository_id INTEGER NOT NULL,
                    task_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    UNIQUE(request_id, event_type, state)
                )
            """)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_dispatcher_audit_request "
                "ON dispatcher_audit_events(request_id, sequence)"
            )

    @staticmethod
    def _uuid(value: str, field: str) -> str:
        try:
            return str(UUID(value))
        except (TypeError, ValueError, AttributeError) as exc:
            raise AuditEventRejected(f"{field} must be a UUID") from exc

    def append(
        self, *, request_id: str, event_type: str, actor_id: str,
        repository_id: int, task_id: str, state: str,
        occurred_at: datetime, event_id: str | None = None,
    ) -> AuditEvent:
        request = self._uuid(request_id, "request_id")
        event = self._uuid(event_id or str(uuid4()), "event_id")
        if event_type not in _ALLOWED_TYPES:
            raise AuditEventRejected("event_type is not allow-listed")
        if not isinstance(actor_id, str) or not actor_id.isdecimal():
            raise AuditEventRejected("actor_id must be a decimal string")
        if type(repository_id) is not int or repository_id <= 0:
            raise AuditEventRejected("repository_id must be a positive integer")
        if not isinstance(task_id, str) or not task_id or len(task_id) > 128:
            raise AuditEventRejected("task_id is invalid")
        if state not in {"ACK", "RUNNING", "PASS", "FAIL", "BLOCKED", "CANCELLED"}:
            raise AuditEventRejected("state is invalid")
        if not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise AuditEventRejected("occurred_at must be timezone-aware")
        timestamp = occurred_at.astimezone(timezone.utc).isoformat()
        values = (event, request, event_type, actor_id, repository_id, task_id, state, timestamp)
        try:
            with self._database.connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT INTO dispatcher_audit_events "
                    "(event_id, request_id, event_type, actor_id, repository_id, task_id, state, occurred_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", values
                )
                connection.commit()
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                raise AuditEventRejected("duplicate audit event or request transition") from exc
            raise
        return AuditEvent(event, request, event_type, actor_id, repository_id, task_id, state,
                          datetime.fromisoformat(timestamp))

    def list_for_request(self, request_id: str) -> tuple[AuditEvent, ...]:
        request = self._uuid(request_id, "request_id")
        with self._database.connection() as connection:
            rows = connection.execute(
                "SELECT event_id, request_id, event_type, actor_id, repository_id, "
                "task_id, state, occurred_at FROM dispatcher_audit_events "
                "WHERE request_id = ? ORDER BY sequence", (request,)
            ).fetchall()
        return tuple(AuditEvent(
            row["event_id"], row["request_id"], row["event_type"], row["actor_id"],
            row["repository_id"], row["task_id"], row["state"],
            datetime.fromisoformat(row["occurred_at"])
        ) for row in rows)
