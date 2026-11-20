"""Deterministic task ranking primitives for the intelligent task engine."""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any, Iterable, Mapping

_STATUS_ORDER = {"in_progress": 0, "todo": 1, "blocked": 2, "done": 3}
_PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
_MISSING_DATE = datetime.max.replace(tzinfo=timezone.utc)


def _parse_timestamp(value: Any) -> datetime:
    """Parse ISO date/timestamp values; invalid or absent values sort last."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    elif isinstance(value, str) and value.strip():
        raw = value.strip()
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = datetime.combine(date.fromisoformat(raw), time.min)
            except ValueError:
                return _MISSING_DATE
    else:
        return _MISSING_DATE

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class IntelligentTaskEngine:
    """Read-only ranking engine; it never mutates persisted task records."""

    def __init__(self, repository: Any) -> None:
        self.repository = repository

    @staticmethod
    def rank_tasks(tasks: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        """Return copied tasks in deterministic actionable-first order.

        Ordering: in-progress, todo, blocked, done; then critical-to-low
        priority; earliest valid due date; earliest creation time; task ID.
        Missing/invalid dates sort after valid dates. Unknown status/priority
        values sort after the supported values within their respective group.
        """
        prepared: list[tuple[tuple[Any, ...], dict[str, Any], list[str]]] = []
        for task in tasks:
            if not isinstance(task, Mapping):
                raise ValueError("Each task must be a mapping")
            item = dict(task)
            task_id = item.get("id")
            if not isinstance(task_id, str) or not task_id.strip():
                raise ValueError("Each task must have a non-empty string id")

            status = str(item.get("status") or "").strip().lower()
            priority = str(item.get("priority") or "").strip().lower()
            status_order = _STATUS_ORDER.get(status, len(_STATUS_ORDER))
            priority_order = _PRIORITY_ORDER.get(priority, len(_PRIORITY_ORDER))
            due = _parse_timestamp(item.get("due_at"))
            created = _parse_timestamp(item.get("created_at"))

            reasons: list[str] = []
            if status == "in_progress":
                reasons.append("Already in progress")
            elif status == "todo":
                reasons.append("Ready to start")
            elif status == "blocked":
                reasons.append("Blocked")
            elif status == "done":
                reasons.append("Already completed")
            else:
                reasons.append("Unknown status; ranked after supported states")

            if priority in _PRIORITY_ORDER:
                reasons.append(f"{priority.title()} priority")
            else:
                reasons.append("Unknown priority; ranked after supported priorities")
            if due != _MISSING_DATE:
                reasons.append(f"Due {due.date().isoformat()}")
            else:
                reasons.append("No valid due date")
            key = (status_order, priority_order, due, created, task_id.casefold(), task_id)
            prepared.append((key, item, reasons))

        prepared.sort(key=lambda entry: entry[0])
        ranked: list[dict[str, Any]] = []
        for position, (_, item, reasons) in enumerate(prepared, start=1):
            item["rank"] = position
            item["ranking_reason"] = reasons
            ranked.append(item)
        return ranked

    def rank_project_tasks(self, project_id: str) -> list[dict[str, Any]]:
        """Rank all tasks belonging to an existing project."""
        if self.repository.get_project(project_id) is None:
            raise KeyError(project_id)
        return self.rank_tasks(self.repository.list_tasks(project_id))
