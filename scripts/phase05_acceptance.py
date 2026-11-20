"""File-backed acceptance workflow for Phase 05 project management."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Direct script execution puts scripts/ rather than the repository root at
# sys.path[0]. Add the root so imports work both as a script and under pytest.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import Database, ProjectRepository
from services import ProjectManagementService


def run_acceptance() -> list[str]:
    """Run a realistic project lifecycle against a temporary SQLite file."""
    checks: list[str] = []
    with tempfile.TemporaryDirectory(prefix="project-continue-p05-") as directory:
        database_path = Path(directory) / "acceptance.sqlite3"
        database = Database(database_path)
        repository = ProjectRepository(database)
        repository.initialize()
        service = ProjectManagementService(repository)

        project = service.create_project("Phase 05 Acceptance", "File-backed lifecycle test")
        checks.append("project registration and persistence")
        repository.create_task("p05-done", project["id"], "Completed task", status="done")
        repository.create_task("p05-open", project["id"], "Open task", status="in_progress")
        details = service.get_project_details(project["id"])
        assert details is not None and details["progress_percent"] == 50.0
        assert details["task_status_counts"]["in_progress"] == 1
        checks.append("task-derived progress and status breakdown")

        updated = service.update_project(project["id"], description="Updated acceptance description")
        assert updated["description"] == "Updated acceptance description"
        assert updated["activity"][0]["event_type"] == "project.updated"
        checks.append("metadata update and activity history")

        archived = service.archive_project(project["id"])
        assert archived["status"] == "archived"
        assert service.list_projects(status="active") == []
        assert len(service.list_projects(status="archived")) == 1
        service.restore_project(project["id"])
        checks.append("archive, filtering, and restore")
        database.close()

        reopened = Database(database_path)
        reopened_repository = ProjectRepository(reopened)
        reopened_repository.initialize()
        reopened_service = ProjectManagementService(reopened_repository)
        persisted = reopened_service.get_project_details(project["id"])
        assert persisted is not None
        assert persisted["status"] == "active"
        assert persisted["total_tasks"] == 2
        assert persisted["progress_percent"] == 50.0
        assert len(persisted["activity"]) >= 4
        with reopened.connection() as connection:
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        checks.append("reopen persistence and SQLite integrity_check")
        reopened.close()
    return checks


def main() -> int:
    checks = run_acceptance()
    for check in checks:
        print(f"[PASS] {check}")
    print(f"PHASE 05 FILE-BACKED ACCEPTANCE: {len(checks)}/{len(checks)} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
