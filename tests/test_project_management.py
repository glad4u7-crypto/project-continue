import pytest

from database import Database, ProjectRepository
from services import ProjectManagementService


@pytest.fixture
def service(tmp_path):
    database = Database(tmp_path / "projects.sqlite3")
    repository = ProjectRepository(database)
    repository.initialize()
    return ProjectManagementService(repository)


def test_create_project_generates_id_and_records_activity(service):
    project = service.create_project("  Launch Plan  ", "  First release  ")
    assert project["name"] == "Launch Plan"
    assert project["description"] == "First release"
    assert project["id"].startswith("prj-")
    assert project["status"] == "active"
    assert project["activity"][0]["event_type"] == "project.created"


def test_create_project_rejects_invalid_name_and_description(service):
    with pytest.raises(ValueError):
        service.create_project("  ")
    with pytest.raises(ValueError, match="2000"):
        service.create_project("Valid", "x" * 2001)


def test_project_list_filters_by_status_and_search(service):
    active = service.create_project("Alpha", "Mobile app")
    archived = service.create_project("Beta", "Internal tools")
    service.archive_project(archived["id"])
    assert [p["id"] for p in service.list_projects(status="active")] == [active["id"]]
    assert [p["id"] for p in service.list_projects(status="archived")] == [archived["id"]]
    assert [p["id"] for p in service.list_projects(query="MOBILE")] == [active["id"]]


def test_project_update_persists_metadata_and_activity(service):
    project = service.create_project("Before")
    updated = service.update_project(project["id"], name="After", description="Updated description")
    assert updated["name"] == "After"
    assert updated["description"] == "Updated description"
    assert updated["activity"][0]["event_type"] == "project.updated"


def test_archive_and_restore_are_idempotent(service):
    project = service.create_project("Lifecycle")
    archived = service.archive_project(project["id"])
    assert archived["status"] == "archived"
    event_count = len(archived["activity"])
    again = service.archive_project(project["id"])
    assert len(again["activity"]) == event_count
    restored = service.restore_project(project["id"])
    assert restored["status"] == "active"
    assert restored["activity"][0]["event_type"] == "project.restored"


def test_project_progress_uses_task_statuses(service):
    project = service.create_project("Progress")
    service.repository.create_task("t-1", project["id"], "One", status="done")
    service.repository.create_task("t-2", project["id"], "Two", status="in_progress")
    service.repository.create_task("t-3", project["id"], "Three", status="todo")
    details = service.get_project_details(project["id"])
    assert details["total_tasks"] == 3
    assert details["completed_tasks"] == 1
    assert details["remaining_tasks"] == 2
    assert details["progress_percent"] == pytest.approx(33.3)
    assert details["task_status_counts"] == {"todo": 1, "in_progress": 1, "blocked": 0, "done": 1}


def test_empty_project_progress_is_zero(service):
    project = service.create_project("Empty")
    details = service.get_project_details(project["id"])
    assert details["progress_percent"] == 0.0
    assert details["total_tasks"] == 0


def test_missing_project_update_archive_and_restore_raise_key_error(service):
    with pytest.raises(KeyError):
        service.update_project("missing", name="Nope")
    with pytest.raises(KeyError):
        service.archive_project("missing")
    with pytest.raises(KeyError):
        service.restore_project("missing")


def test_invalid_project_status_filter_is_rejected(service):
    with pytest.raises(ValueError, match="Status filter"):
        service.list_projects(status="deleted")
