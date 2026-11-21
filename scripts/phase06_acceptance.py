"""Isolated file-backed acceptance workflow for Phase 06 task management."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Make direct execution (python scripts/phase06_acceptance.py) resolve the
# repository's top-level packages exactly as pytest does.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import Database, ProjectRepository
from services import ProjectManagementService, TaskManagementService


def run_acceptance() -> list[str]:
    checks: list[str] = []
    with tempfile.TemporaryDirectory(prefix="project-continue-p06-") as directory:
        database_path = Path(directory) / "tasks.sqlite3"
        database = Database(database_path)
        repository = ProjectRepository(database)
        repository.initialize()
        projects = ProjectManagementService(repository)
        tasks = TaskManagementService(repository)
        project = projects.create_project("Phase 06 Acceptance")
        other = projects.create_project("Phase 06 Other Project")

        prerequisite = tasks.create_task(
            project["id"], "Prepare prerequisite", description="Initial work",
            assignee="Alex", priority="high", due_at="2026-12-01",
        )
        dependent = tasks.create_task(
            project["id"], "Deliver dependent task", priority="critical",
        )
        other_task = tasks.create_task(other["id"], "Other project task")
        assert prerequisite["assignee"] == "Alex"
        assert tasks.list_tasks(project["id"], priority="high")[0]["id"] == prerequisite["id"]
        assert tasks.list_tasks(project["id"], query="prerequisite")[0]["id"] == prerequisite["id"]
        checks.append("task creation, generated IDs, assignment, priority, due date and filters")

        updated = tasks.update_task(
            prerequisite["id"], title="Prepare updated prerequisite",
            description="Revised work", assignee="Taylor", priority="medium",
            status="in_progress", due_at="2026-12-05",
        )
        assert updated["title"] == "Prepare updated prerequisite"
        assert updated["assignee"] == "Taylor" and updated["status"] == "in_progress"
        tasks.assign_task(prerequisite["id"], None)
        assert tasks.get_task_details(prerequisite["id"])["assignee"] is None
        checks.append("task update, status transition and assignment clear")

        tasks.add_dependency(dependent["id"], prerequisite["id"])
        assert tasks.get_task_details(dependent["id"])["can_complete"] is False
        try:
            tasks.complete_task(dependent["id"])
        except ValueError as error:
            assert "prerequisite" in str(error).lower()
        else:
            raise AssertionError("A task with an unfinished prerequisite was completed")
        try:
            tasks.add_dependency(prerequisite["id"], dependent["id"])
        except ValueError as error:
            assert "cycle" in str(error).lower()
        else:
            raise AssertionError("A dependency cycle was accepted")
        try:
            tasks.add_dependency(dependent["id"], other_task["id"])
        except ValueError as error:
            assert "same project" in str(error).lower()
        else:
            raise AssertionError("A cross-project dependency was accepted")
        checks.append("dependency creation, completion gate, cycle and cross-project rejection")

        tasks.complete_task(prerequisite["id"])
        tasks.complete_task(dependent["id"])
        assert tasks.get_task_details(dependent["id"])["can_complete"] is True
        tasks.remove_dependency(dependent["id"], prerequisite["id"])
        checks.append("dependency-aware completion and dependency removal")

        events = [event["event_type"] for event in repository.list_activity(project["id"])]
        assert "task.created" in events and "task.updated" in events
        assert "task.completed" in events and "task.dependency_added" in events
        checks.append("task activity and audit history")

        database.close()
        reopened = Database(database_path)
        reopened_repository = ProjectRepository(reopened)
        reopened_repository.initialize()
        reopened_tasks = TaskManagementService(reopened_repository)
        assert reopened_tasks.get_task_details(dependent["id"])["status"] == "done"
        assert reopened_tasks.get_task_details(prerequisite["id"])["assignee"] is None
        with reopened.connection() as connection:
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        checks.append("file-backed persistence after close/reopen and SQLite integrity")

        backup_path = Path(directory) / "tasks-backup.sqlite3"
        reopened.backup(backup_path)
        assert Database.verify_backup(backup_path)
        backup_db = Database(backup_path)
        backup_repo = ProjectRepository(backup_db)
        backup_repo.initialize()
        assert backup_repo.get_task(dependent["id"])["status"] == "done"
        backup_db.close()
        checks.append("verified backup contains persisted task records")
        reopened.close()
    return checks


def main() -> int:
    checks = run_acceptance()
    for check in checks:
        print(f"[PASS] {check}")
    print(f"PHASE 06 FILE-BACKED ACCEPTANCE: {len(checks)}/{len(checks)} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
