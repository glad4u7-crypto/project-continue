import pytest

pytestmark = pytest.mark.integration

from database import Database, ProjectRepository
from services import IntelligentTaskEngine, ProjectManagementService, TaskManagementService


@pytest.fixture
def engine_workspace(tmp_path):
    db = Database(tmp_path / "phase07.db")
    repository = ProjectRepository(db)
    repository.initialize()
    project = ProjectManagementService(repository).create_project("Phase 07")
    service = TaskManagementService(repository)
    return repository, service, IntelligentTaskEngine(repository), project["id"]


def test_priority_score_is_explainable_and_due_date_aware(engine_workspace):
    _, _, engine, _ = engine_workspace
    critical = {"id": "critical", "priority": "critical", "status": "todo", "due_at": "2026-11-21"}
    low = {"id": "low", "priority": "low", "status": "todo", "due_at": "2026-12-30"}
    assert engine.calculate_priority(critical, as_of="2026-11-20")["score"] > engine.calculate_priority(low, as_of="2026-11-20")["score"]
    assert engine.calculate_priority({**critical, "status": "done"})["score"] == 0
    assert engine.calculate_priority(critical, as_of="2026-11-20")["reasons"]


def test_dependency_analysis_includes_transitive_prerequisites(engine_workspace):
    _, tasks, engine, pid = engine_workspace
    a = tasks.create_task(pid, "A")
    b = tasks.create_task(pid, "B")
    c = tasks.create_task(pid, "C")
    tasks.add_dependency(b["id"], a["id"])
    tasks.add_dependency(c["id"], b["id"])
    analysis = engine.analyze_dependencies(c["id"])
    assert {x["id"] for x in analysis["dependencies"]} == {a["id"], b["id"]}
    assert not analysis["ready"]
    assert {x["id"] for x in analysis["pending_dependencies"]} == {a["id"], b["id"]}


def test_dependency_analysis_becomes_ready_after_prerequisites_complete(engine_workspace):
    _, tasks, engine, pid = engine_workspace
    a = tasks.create_task(pid, "A")
    b = tasks.create_task(pid, "B")
    tasks.add_dependency(b["id"], a["id"])
    tasks.complete_task(a["id"])
    assert engine.analyze_dependencies(b["id"])["ready"] is True


def test_next_task_ignores_blocked_and_done_and_chooses_highest_score(engine_workspace):
    _, tasks, engine, pid = engine_workspace
    blocked = tasks.create_task(pid, "Blocked", priority="critical")
    tasks.set_status(blocked["id"], "blocked")
    waiting = tasks.create_task(pid, "Waiting", priority="critical")
    prerequisite = tasks.create_task(pid, "Prerequisite")
    tasks.add_dependency(waiting["id"], prerequisite["id"])
    done = tasks.create_task(pid, "Done", priority="critical")
    tasks.complete_task(done["id"])
    ready = tasks.create_task(pid, "Ready", priority="high")
    selected = engine.select_next_task(pid, as_of="2026-11-20")
    assert selected["id"] == ready["id"]


def test_blocked_detection_and_recommendations(engine_workspace):
    _, tasks, engine, pid = engine_workspace
    prerequisite = tasks.create_task(pid, "Prerequisite")
    waiting = tasks.create_task(pid, "Waiting")
    tasks.add_dependency(waiting["id"], prerequisite["id"])
    explicit = tasks.create_task(pid, "Explicit")
    tasks.set_status(explicit["id"], "blocked")
    blocked = engine.detect_blocked_tasks(pid)
    assert {item["task"]["id"] for item in blocked} == {waiting["id"], explicit["id"]}
    actions = engine.recommend_actions(pid)
    by_id = {item["task_id"]: item["action"] for item in actions}
    assert by_id[waiting["id"]] == "unblock"
    assert by_id[explicit["id"]] == "unblock"
    assert by_id[prerequisite["id"]] == "start"


def test_completion_verification_checks_status_and_prerequisites(engine_workspace):
    _, tasks, engine, pid = engine_workspace
    prerequisite = tasks.create_task(pid, "Prerequisite")
    dependent = tasks.create_task(pid, "Dependent")
    tasks.add_dependency(dependent["id"], prerequisite["id"])
    before = engine.verify_completion(dependent["id"])
    assert before["verified"] is False
    tasks.complete_task(prerequisite["id"])
    tasks.complete_task(dependent["id"])
    after = engine.verify_completion(dependent["id"])
    assert after["verified"] is True
    assert after["errors"] == []


def test_project_methods_validate_project_and_recommendation_limit(engine_workspace):
    _, tasks, engine, pid = engine_workspace
    for name in ("A", "B", "C"):
        tasks.create_task(pid, name)
    assert len(engine.recommend_actions(pid, limit=2)) == 2
    with pytest.raises(ValueError):
        engine.recommend_actions(pid, limit=0)
    with pytest.raises(KeyError):
        engine.select_next_task("missing-project")


def test_intelligent_methods_do_not_mutate_repository_tasks(engine_workspace):
    repository, tasks, engine, pid = engine_workspace
    task = tasks.create_task(pid, "Read only", priority="high")
    before = repository.get_task(task["id"])
    engine.rank_project_tasks(pid)
    engine.calculate_project_priorities(pid, as_of="2026-11-20")
    engine.select_next_task(pid, as_of="2026-11-20")
    engine.recommend_actions(pid, as_of="2026-11-20")
    assert repository.get_task(task["id"]) == before
