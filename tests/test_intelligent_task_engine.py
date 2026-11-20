import pytest

pytestmark = pytest.mark.unit

from database import Database, ProjectRepository
from services import IntelligentTaskEngine, ProjectManagementService, TaskManagementService


@pytest.fixture
def workspace(tmp_path):
    database = Database(tmp_path / "ranking.db")
    repository = ProjectRepository(database)
    repository.initialize()
    project = ProjectManagementService(repository).create_project("Ranking workspace")
    return repository, TaskManagementService(repository), project["id"]


def test_rank_tasks_uses_status_priority_due_date_and_stable_tiebreakers(workspace):
    repository, tasks, project_id = workspace
    engine = IntelligentTaskEngine(repository)
    records = [
        tasks.create_task(project_id, "Low todo", priority="low", due_at="2026-12-01"),
        tasks.create_task(project_id, "Critical todo", priority="critical", due_at="2026-12-20"),
        tasks.create_task(project_id, "High in progress", priority="high", status="in_progress"),
        tasks.create_task(project_id, "Blocked critical", priority="critical", status="blocked"),
        tasks.create_task(project_id, "Done critical", priority="critical", status="done"),
        tasks.create_task(project_id, "Medium earlier", priority="medium", due_at="2026-11-21"),
        tasks.create_task(project_id, "Medium later", priority="medium", due_at="2026-11-25"),
    ]

    ranked = engine.rank_tasks(records)

    assert [item["title"] for item in ranked] == [
        "High in progress",
        "Critical todo",
        "Medium earlier",
        "Medium later",
        "Low todo",
        "Blocked critical",
        "Done critical",
    ]
    assert [item["rank"] for item in ranked] == list(range(1, 8))
    assert "Critical priority" in ranked[1]["ranking_reason"]


def test_rank_tasks_puts_missing_and_invalid_due_dates_after_valid_dates(workspace):
    repository, _, _ = workspace
    engine = IntelligentTaskEngine(repository)
    ranked = engine.rank_tasks([
        {"id": "missing", "status": "todo", "priority": "high"},
        {"id": "invalid", "status": "todo", "priority": "high", "due_at": "not-a-date"},
        {"id": "valid", "status": "todo", "priority": "high", "due_at": "2026-11-21"},
    ])
    assert ranked[0]["id"] == "valid"
    assert {item["id"] for item in ranked[1:]} == {"missing", "invalid"}


def test_rank_tasks_normalizes_timezone_and_does_not_mutate_input(workspace):
    repository, _, _ = workspace
    engine = IntelligentTaskEngine(repository)
    first = {"id": "first", "status": "todo", "priority": "medium",
             "due_at": "2026-11-21T09:30:00+05:30"}
    second = {"id": "second", "status": "todo", "priority": "medium",
              "due_at": "2026-11-21T04:00:00Z"}
    ranked = engine.rank_tasks([first, second])
    assert [item["id"] for item in ranked] == ["first", "second"]
    assert "rank" not in first
    assert "ranking_reason" not in second


def test_rank_tasks_is_deterministic_for_equal_fields(workspace):
    repository, _, _ = workspace
    engine = IntelligentTaskEngine(repository)
    tasks = [
        {"id": "task-b", "status": "todo", "priority": "medium"},
        {"id": "task-a", "status": "todo", "priority": "medium"},
    ]
    assert [item["id"] for item in engine.rank_tasks(tasks)] == ["task-a", "task-b"]


def test_rank_tasks_validates_task_records(workspace):
    repository, _, _ = workspace
    engine = IntelligentTaskEngine(repository)
    with pytest.raises(ValueError, match="mapping"):
        engine.rank_tasks(["not-a-task"])
    with pytest.raises(ValueError, match="id"):
        engine.rank_tasks([{"title": "Missing identifier"}])


def test_rank_project_tasks_reads_only_the_requested_project(workspace):
    repository, tasks, project_id = workspace
    engine = IntelligentTaskEngine(repository)
    tasks.create_task(project_id, "A", priority="low")
    tasks.create_task(project_id, "B", priority="critical")
    ranked = engine.rank_project_tasks(project_id)
    assert [item["title"] for item in ranked] == ["B", "A"]
    with pytest.raises(KeyError):
        engine.rank_project_tasks("missing-project")
