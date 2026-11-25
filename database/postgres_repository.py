"""PostgreSQL implementation of the project/task repository contract."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from core.validation import (
    validate_identifier, validate_priority, validate_project_name,
    validate_task_status, validate_task_title,
)
from database.postgres_connection import PostgresDatabase


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PostgresProjectRepository:
    """PostgreSQL-backed project/task repository; never selected implicitly."""

    def __init__(self, database: PostgresDatabase) -> None:
        self.database = database

    def initialize(self) -> None:
        from database.postgres_schema import initialize_postgres_schema
        initialize_postgres_schema(self.database)

    def create_project(self, project_id: str, name: str, description: str = "") -> dict[str, Any]:
        project_id, name, now = validate_identifier(project_id), validate_project_name(name), _now()
        with self.database.transaction() as c:
            c.execute(
                "INSERT INTO projects(id,name,description,created_at,updated_at) VALUES(%s,%s,%s,%s,%s)",
                (project_id, name, description, now, now),
            )
        return self.get_project(project_id)

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self.database.connection() as c:
            row = c.execute("SELECT * FROM projects WHERE id=%s", (validate_identifier(project_id),)).fetchone()
            return dict(row) if row else None

    def list_projects(self) -> list[dict[str, Any]]:
        with self.database.connection() as c:
            return [dict(r) for r in c.execute("SELECT * FROM projects ORDER BY created_at,id")]

    def update_project(self, project_id: str, *, name: str | None = None,
                       description: str | None = None, status: str | None = None) -> dict[str, Any]:
        project_id = validate_identifier(project_id)
        fields: dict[str, Any] = {}
        if name is not None:
            fields["name"] = validate_project_name(name)
        if description is not None:
            fields["description"] = description
        if status is not None:
            status = status.strip().lower()
            if status not in {"active", "archived"}:
                raise ValueError("Project status must be active or archived")
            fields["status"] = status
        if not fields:
            project = self.get_project(project_id)
            if project is None:
                raise KeyError(project_id)
            return project
        fields["updated_at"] = _now()
        assignments = ",".join(f"{key}=%s" for key in fields)
        with self.database.transaction() as c:
            result = c.execute(f"UPDATE projects SET {assignments} WHERE id=%s",
                               (*fields.values(), project_id))
            if result.rowcount == 0:
                raise KeyError(project_id)
        return self.get_project(project_id)

    def delete_project(self, project_id: str) -> bool:
        with self.database.transaction() as c:
            return c.execute("DELETE FROM projects WHERE id=%s",
                             (validate_identifier(project_id),)).rowcount > 0

    def create_task(self, task_id: str, project_id: str, title: str, *, description: str = "",
                    assignee: str | None = None, priority: str = "medium",
                    status: str = "todo", due_at: str | None = None) -> dict[str, Any]:
        task_id, project_id = validate_identifier(task_id), validate_identifier(project_id)
        title, priority, status, now = validate_task_title(title), validate_priority(priority), validate_task_status(status), _now()
        with self.database.transaction() as c:
            c.execute(
                "INSERT INTO tasks(id,project_id,title,description,assignee,priority,status,due_at,created_at,updated_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (task_id, project_id, title, description, assignee, priority, status, due_at, now, now),
            )
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self.database.connection() as c:
            row = c.execute("SELECT * FROM tasks WHERE id=%s", (validate_identifier(task_id),)).fetchone()
            return dict(row) if row else None

    def list_tasks(self, project_id: str) -> list[dict[str, Any]]:
        with self.database.connection() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM tasks WHERE project_id=%s ORDER BY created_at,id",
                (validate_identifier(project_id),),
            )]

    def update_task(self, task_id: str, *, title: str | None = None, description: str | None = None,
                    assignee: str | None = None, priority: str | None = None,
                    status: str | None = None, due_at: str | None = None) -> dict[str, Any]:
        task_id = validate_identifier(task_id)
        fields: dict[str, Any] = {}
        if title is not None:
            fields["title"] = validate_task_title(title)
        if description is not None:
            fields["description"] = description
        if assignee is not None:
            fields["assignee"] = assignee.strip() or None
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
        assignments = ",".join(f"{key}=%s" for key in fields)
        with self.database.transaction() as c:
            result = c.execute(f"UPDATE tasks SET {assignments} WHERE id=%s",
                               (*fields.values(), task_id))
            if result.rowcount == 0:
                raise KeyError(task_id)
        return self.get_task(task_id)

    def delete_task(self, task_id: str) -> bool:
        with self.database.transaction() as c:
            return c.execute("DELETE FROM tasks WHERE id=%s",
                             (validate_identifier(task_id),)).rowcount > 0

    def add_dependency(self, task_id: str, depends_on_task_id: str) -> None:
        task_id, depends_on_task_id = validate_identifier(task_id), validate_identifier(depends_on_task_id)
        if task_id == depends_on_task_id:
            raise ValueError("A task cannot depend on itself")
        with self.database.transaction() as c:
            rows = c.execute(
                "SELECT id,project_id FROM tasks WHERE id = ANY(%s) FOR UPDATE",
                ([task_id, depends_on_task_id],),
            ).fetchall()
            if len(rows) != 2:
                raise KeyError("Both tasks must exist")
            if len({r["project_id"] for r in rows}) != 1:
                raise ValueError("Task dependencies must belong to the same project")
            cycle = c.execute(
                "WITH RECURSIVE reachable(id) AS ("
                "SELECT depends_on_task_id FROM task_dependencies WHERE task_id=%s "
                "UNION SELECT d.depends_on_task_id FROM task_dependencies d "
                "JOIN reachable r ON d.task_id=r.id) "
                "SELECT 1 FROM reachable WHERE id=%s LIMIT 1",
                (depends_on_task_id, task_id),
            ).fetchone()
            if cycle:
                raise ValueError("Dependency would create a cycle")
            c.execute("INSERT INTO task_dependencies VALUES(%s,%s,%s)",
                      (task_id, depends_on_task_id, _now()))

    def remove_dependency(self, task_id: str, depends_on_task_id: str) -> bool:
        with self.database.transaction() as c:
            return c.execute(
                "DELETE FROM task_dependencies WHERE task_id=%s AND depends_on_task_id=%s",
                (validate_identifier(task_id), validate_identifier(depends_on_task_id)),
            ).rowcount > 0

    def list_dependencies(self, task_id: str) -> list[str]:
        with self.database.connection() as c:
            return [r["depends_on_task_id"] for r in c.execute(
                "SELECT depends_on_task_id FROM task_dependencies WHERE task_id=%s ORDER BY depends_on_task_id",
                (validate_identifier(task_id),),
            )]

    def record_activity(self, project_id: str, event_type: str, *, task_id: str | None = None,
                        payload: dict[str, Any] | None = None) -> int:
        project_id = validate_identifier(project_id)
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("event_type must be non-empty text")
        data, now = json.dumps(payload or {}, sort_keys=True, separators=(",", ":")), _now()
        with self.database.transaction() as c:
            if task_id is not None:
                task_id = validate_identifier(task_id)
                task = c.execute("SELECT project_id FROM tasks WHERE id=%s", (task_id,)).fetchone()
                if task is None:
                    raise KeyError(task_id)
                if task["project_id"] != project_id:
                    raise ValueError("Activity task must belong to the same project")
            row = c.execute(
                "INSERT INTO activity_history(project_id,task_id,event_type,payload_json,created_at) "
                "VALUES(%s,%s,%s,%s,%s) RETURNING id",
                (project_id, task_id, event_type.strip(), data, now),
            ).fetchone()
            return int(row["id"])

    def list_activity(self, project_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        with self.database.connection() as c:
            items = []
            for row in c.execute(
                "SELECT * FROM activity_history WHERE project_id=%s ORDER BY id DESC LIMIT %s",
                (validate_identifier(project_id), limit),
            ):
                item = dict(row)
                item["payload"] = json.loads(item.pop("payload_json"))
                items.append(item)
            return items
