"""Validated CRUD operations for the SQLite persistence layer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from core.validation import (
    validate_identifier,
    validate_priority,
    validate_project_name,
    validate_task_status,
    validate_task_title,
)
from database.connection import Database
from database.schema import SCHEMA_SQL


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectRepository:
    """Project/task/dependency/activity repository backed by SQLite."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def initialize(self) -> None:
        with self.database.connection() as connection:
            connection.executescript(SCHEMA_SQL)

    def create_project(self, project_id: str, name: str, description: str = "") -> dict[str, Any]:
        project_id = validate_identifier(project_id)
        name = validate_project_name(name)
        now = _now()
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO projects(id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (project_id, name, description, now, now),
            )
        return self.get_project(project_id)

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM projects WHERE id = ?", (validate_identifier(project_id),)).fetchone()
            return dict(row) if row else None

    def list_projects(self) -> list[dict[str, Any]]:
        with self.database.connection() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM projects ORDER BY created_at, id")]

    def update_project(self, project_id: str, *, name: str | None = None,
                       description: str | None = None, status: str | None = None) -> dict[str, Any]:
        project_id = validate_identifier(project_id)
        fields: dict[str, Any] = {}
        if name is not None:
            fields["name"] = validate_project_name(name)
        if description is not None:
            fields["description"] = description
        if status is not None:
            normalized = status.strip().lower()
            if normalized not in {"active", "archived"}:
                raise ValueError("Project status must be active or archived")
            fields["status"] = normalized
        if not fields:
            project = self.get_project(project_id)
            if project is None:
                raise KeyError(project_id)
            return project
        fields["updated_at"] = _now()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        with self.database.transaction() as connection:
            cursor = connection.execute(
                f"UPDATE projects SET {assignments} WHERE id = ?",
                (*fields.values(), project_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(project_id)
        return self.get_project(project_id)

    def delete_project(self, project_id: str) -> bool:
        with self.database.transaction() as connection:
            cursor = connection.execute("DELETE FROM projects WHERE id = ?", (validate_identifier(project_id),))
            return cursor.rowcount > 0

    def create_task(self, task_id: str, project_id: str, title: str, *,
                    description: str = "", priority: str = "medium",
                    status: str = "todo", due_at: str | None = None) -> dict[str, Any]:
        task_id = validate_identifier(task_id)
        project_id = validate_identifier(project_id)
        title = validate_task_title(title)
        priority = validate_priority(priority)
        status = validate_task_status(status)
        now = _now()
        with self.database.transaction() as connection:
            connection.execute(
                """INSERT INTO tasks
                   (id, project_id, title, description, priority, status, due_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (task_id, project_id, title, description, priority, status, due_at, now, now),
            )
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (validate_identifier(task_id),)).fetchone()
            return dict(row) if row else None

    def list_tasks(self, project_id: str) -> list[dict[str, Any]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM tasks WHERE project_id = ? ORDER BY created_at, id",
                (validate_identifier(project_id),),
            )
            return [dict(row) for row in rows]

    def update_task(self, task_id: str, *, title: str | None = None,
                    description: str | None = None, priority: str | None = None,
                    status: str | None = None, due_at: str | None = None) -> dict[str, Any]:
        task_id = validate_identifier(task_id)
        fields: dict[str, Any] = {}
        if title is not None:
            fields["title"] = validate_task_title(title)
        if description is not None:
            fields["description"] = description
        if priority is not None:
            fields["priority"] = validate_priority(priority)
        if status is not None:
            fields["status"] = validate_task_status(status)
        if due_at is not None:
            fields["due_at"] = due_at
        if not fields:
            task = self.get_task(task_id)
            if task is None:
                raise KeyError(task_id)
            return task
        fields["updated_at"] = _now()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        with self.database.transaction() as connection:
            cursor = connection.execute(
                f"UPDATE tasks SET {assignments} WHERE id = ?",
                (*fields.values(), task_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(task_id)
        return self.get_task(task_id)

    def delete_task(self, task_id: str) -> bool:
        with self.database.transaction() as connection:
            cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (validate_identifier(task_id),))
            return cursor.rowcount > 0

    def add_dependency(self, task_id: str, depends_on_task_id: str) -> None:
        task_id = validate_identifier(task_id)
        depends_on_task_id = validate_identifier(depends_on_task_id)
        if task_id == depends_on_task_id:
            raise ValueError("A task cannot depend on itself")
        with self.database.transaction() as connection:
            rows = connection.execute(
                "SELECT id, project_id FROM tasks WHERE id IN (?, ?)",
                (task_id, depends_on_task_id),
            ).fetchall()
            if len(rows) != 2:
                raise KeyError("Both tasks must exist")
            projects = {row["project_id"] for row in rows}
            if len(projects) != 1:
                raise ValueError("Task dependencies must belong to the same project")
            cycle = connection.execute(
                """WITH RECURSIVE reachable(task_id) AS (
                       SELECT depends_on_task_id FROM task_dependencies WHERE task_id = ?
                       UNION
                       SELECT d.depends_on_task_id
                       FROM task_dependencies d JOIN reachable r ON d.task_id = r.task_id
                   )
                   SELECT 1 FROM reachable WHERE task_id = ? LIMIT 1""",
                (depends_on_task_id, task_id),
            ).fetchone()
            if cycle:
                raise ValueError("Dependency would create a cycle")
            connection.execute(
                "INSERT INTO task_dependencies(task_id, depends_on_task_id, created_at) VALUES (?, ?, ?)",
                (task_id, depends_on_task_id, _now()),
            )

    def list_dependencies(self, task_id: str) -> list[str]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT depends_on_task_id FROM task_dependencies WHERE task_id = ? ORDER BY depends_on_task_id",
                (validate_identifier(task_id),),
            )
            return [row["depends_on_task_id"] for row in rows]

    def record_activity(self, project_id: str, event_type: str, *,
                        task_id: str | None = None, payload: dict[str, Any] | None = None) -> int:
        project_id = validate_identifier(project_id)
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("event_type must be non-empty text")
        payload_json = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
        with self.database.transaction() as connection:
            if task_id is not None:
                task_id = validate_identifier(task_id)
                task = connection.execute(
                    "SELECT project_id FROM tasks WHERE id = ?",
                    (task_id,),
                ).fetchone()
                if task is None:
                    raise KeyError(task_id)
                if task["project_id"] != project_id:
                    raise ValueError("Activity task must belong to the same project")
            cursor = connection.execute(
                """INSERT INTO activity_history(project_id, task_id, event_type, payload_json, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (project_id, task_id, event_type.strip(), payload_json, _now()),
            )
            return int(cursor.lastrowid)

    def list_activity(self, project_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        with self.database.connection() as connection:
            rows = connection.execute(
                """SELECT * FROM activity_history WHERE project_id = ?
                   ORDER BY id DESC LIMIT ?""",
                (validate_identifier(project_id), limit),
            )
            result = []
            for row in rows:
                item = dict(row)
                item["payload"] = json.loads(item.pop("payload_json"))
                result.append(item)
            return result
