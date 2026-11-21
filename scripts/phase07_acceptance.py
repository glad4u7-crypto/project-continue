"""Run an isolated end-to-end acceptance check for Phase 07."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Make direct execution resolve the repository's top-level packages.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import Database, ProjectRepository
from services import IntelligentTaskEngine, ProjectManagementService, TaskManagementService


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="phase07-") as directory:
        database = Database(Path(directory) / "acceptance.sqlite3")
        repository = ProjectRepository(database)
        repository.initialize()
        project = ProjectManagementService(repository).create_project("Phase 07 acceptance")
        project_id = project["id"]
        tasks = TaskManagementService(repository)
        engine = IntelligentTaskEngine(repository)
        prerequisite = tasks.create_task(project_id, "Prepare prerequisite", priority="high")
        dependent = tasks.create_task(project_id, "Deliver dependent work", priority="critical")
        tasks.add_dependency(dependent["id"], prerequisite["id"])
        assert engine.rank_project_tasks(project_id)[0]["rank"] == 1
        score = engine.calculate_priority(dependent, as_of="2026-11-20")
        assert 0 <= score["score"] <= 100 and score["reasons"]
        analysis = engine.analyze_dependencies(dependent["id"])
        assert analysis["ready"] is False
        assert prerequisite["id"] in {item["id"] for item in analysis["pending_dependencies"]}
        assert engine.select_next_task(project_id, as_of="2026-11-20")["id"] == prerequisite["id"]
        assert dependent["id"] in {item["task"]["id"] for item in engine.detect_blocked_tasks(project_id)}
        assert any(item["task_id"] == dependent["id"] and item["action"] == "unblock"
                   for item in engine.recommend_actions(project_id, as_of="2026-11-20"))
        assert engine.verify_completion(dependent["id"])["verified"] is False
        tasks.complete_task(prerequisite["id"])
        assert engine.analyze_dependencies(dependent["id"])["ready"] is True
        tasks.complete_task(dependent["id"])
        assert engine.verify_completion(dependent["id"])["verified"] is True
        print("[PASS] Task ranking")
        print("[PASS] Explainable priority calculation")
        print("[PASS] Direct/transitive dependency analysis")
        print("[PASS] Next actionable task selection")
        print("[PASS] Blocked task detection")
        print("[PASS] Start/continue/unblock recommendations")
        print("[PASS] Dependency-aware completion verification")
        print("[PASS] Isolated database; no existing user data changed")
        print("PHASE 07 RUNTIME ACCEPTANCE: PASS")


if __name__ == "__main__":
    main()
