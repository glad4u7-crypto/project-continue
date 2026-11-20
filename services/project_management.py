"""Use-case services for managing projects on the existing SQLite repository."""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from core.validation import validate_project_name
from database.repository import ProjectRepository


class ProjectManagementService:
    """Project lifecycle and read-model operations without duplicating persistence."""

    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    @staticmethod
    def _description(value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Project description must be text")
        normalized = value.strip()
        if len(normalized) > 2000:
            raise ValueError("Project description must be 2000 characters or fewer")
        return normalized

    def _ensure_unique_name(self, name: str, *, exclude_project_id: str | None = None) -> None:
        folded = name.casefold()
        for project in self.repository.list_projects():
            if project["id"] != exclude_project_id and project["name"].casefold() == folded:
                raise ValueError("A project with this name already exists")

    @staticmethod
    def _translate_integrity_error(error: sqlite3.IntegrityError) -> ValueError:
        if "projects.name" in str(error):
            return ValueError("A project with this name already exists")
        return ValueError("Project data violates a database constraint")

    def create_project(self, name: str, description: str = "", *, project_id: str | None = None) -> dict[str, Any]:
        """Create a project and record its initial activity event."""
        normalized_name = validate_project_name(name)
        normalized_description = self._description(description)
        self._ensure_unique_name(normalized_name)
        identifier = project_id or f"prj-{uuid.uuid4().hex[:12]}"
        try:
            self.repository.create_project(identifier, normalized_name, normalized_description)
        except sqlite3.IntegrityError as exc:
            raise self._translate_integrity_error(exc) from exc
        self.repository.record_activity(identifier, "project.created", payload={"name": normalized_name})
        return self.get_project_details(identifier)  # type: ignore[return-value]

    def update_project(self, project_id: str, *, name: str | None = None,
                       description: str | None = None) -> dict[str, Any]:
        """Update editable project metadata and record the changed fields."""
        if self.repository.get_project(project_id) is None:
            raise KeyError(project_id)
        changes: dict[str, Any] = {}
        if name is not None:
            changes["name"] = validate_project_name(name)
            self._ensure_unique_name(changes["name"], exclude_project_id=project_id)
        if description is not None:
            changes["description"] = self._description(description)
        if not changes:
            return self.get_project_details(project_id)  # type: ignore[return-value]
        try:
            updated = self.repository.update_project(project_id, **changes)
        except sqlite3.IntegrityError as exc:
            raise self._translate_integrity_error(exc) from exc
        self.repository.record_activity(project_id, "project.updated", payload={"fields": sorted(changes)})
        return self.get_project_details(project_id) or updated

    def archive_project(self, project_id: str) -> dict[str, Any]:
        """Archive an active project; repeated archive requests are idempotent."""
        project = self.repository.get_project(project_id)
        if project is None:
            raise KeyError(project_id)
        if project["status"] != "archived":
            self.repository.update_project(project_id, status="archived")
            self.repository.record_activity(project_id, "project.archived")
        return self.get_project_details(project_id)  # type: ignore[return-value]

    def restore_project(self, project_id: str) -> dict[str, Any]:
        """Restore an archived project to active status."""
        project = self.repository.get_project(project_id)
        if project is None:
            raise KeyError(project_id)
        if project["status"] != "active":
            self.repository.update_project(project_id, status="active")
            self.repository.record_activity(project_id, "project.restored")
        return self.get_project_details(project_id)  # type: ignore[return-value]

    def _progress(self, project_id: str) -> dict[str, Any]:
        tasks = self.repository.list_tasks(project_id)
        total = len(tasks)
        done = sum(task["status"] == "done" for task in tasks)
        status_counts = {status: sum(task["status"] == status for task in tasks)
                         for status in ("todo", "in_progress", "blocked", "done")}
        return {
            "total_tasks": total,
            "completed_tasks": done,
            "remaining_tasks": total - done,
            "progress_percent": round((done / total) * 100, 1) if total else 0.0,
            "task_status_counts": status_counts,
        }

    def list_projects(self, *, status: str = "all", query: str = "") -> list[dict[str, Any]]:
        """List projects with progress summaries and optional status/name filtering."""
        normalized_status = status.strip().lower()
        if normalized_status not in {"all", "active", "archived"}:
            raise ValueError("Status filter must be all, active, or archived")
        normalized_query = query.strip().casefold()
        projects = self.repository.list_projects()
        result = []
        for project in projects:
            if normalized_status != "all" and project["status"] != normalized_status:
                continue
            if normalized_query and normalized_query not in (project["name"] + " " + project["description"]).casefold():
                continue
            result.append({**project, **self._progress(project["id"])})
        return result

    def get_project_details(self, project_id: str) -> dict[str, Any] | None:
        """Return project metadata, task progress, and recent activity."""
        project = self.repository.get_project(project_id)
        if project is None:
            return None
        return {
            **project,
            **self._progress(project_id),
            "tasks": self.repository.list_tasks(project_id),
            "activity": self.repository.list_activity(project_id, limit=25),
        }
