import sqlite3

import pytest

from database import Database, ProjectRepository


@pytest.fixture
def repository(tmp_path):
    repo = ProjectRepository(Database(tmp_path / "project.db"))
    repo.initialize()
    return repo


def test_project_and_task_crud(repository):
    project = repository.create_project("p-1", "Demo Project", "first")
    assert project["name"] == "Demo Project"
    task = repository.create_task("t-1", "p-1", "Build database", priority="HIGH")
    assert task["priority"] == "high"
    assert repository.get_task("t-1")["title"] == "Build database"
    updated = repository.update_task("t-1", status="in_progress", title="Build SQLite")
    assert updated["status"] == "in_progress"
    assert updated["title"] == "Build SQLite"
    assert repository.list_tasks("p-1")[0]["id"] == "t-1"
    assert repository.update_project("p-1", status="archived")["status"] == "archived"
    assert repository.delete_task("t-1") is True
    assert repository.get_task("t-1") is None
    assert repository.delete_project("p-1") is True


def test_foreign_keys_and_dependency_constraints(repository):
    repository.create_project("p-1", "Demo")
    repository.create_task("t-1", "p-1", "One")
    repository.create_task("t-2", "p-1", "Two")
    repository.create_task("t-3", "p-1", "Three")
    repository.add_dependency("t-2", "t-1")
    repository.add_dependency("t-3", "t-2")
    assert repository.list_dependencies("t-3") == ["t-2"]
    with pytest.raises(ValueError, match="cycle"):
        repository.add_dependency("t-1", "t-3")
    with pytest.raises(ValueError, match="itself"):
        repository.add_dependency("t-1", "t-1")
    with pytest.raises(Exception):
        repository.create_task("orphan", "missing-project", "Orphan")


def test_dependencies_cannot_cross_projects(repository):
    repository.create_project("p-1", "One")
    repository.create_project("p-2", "Two")
    repository.create_task("t-1", "p-1", "One")
    repository.create_task("t-2", "p-2", "Two")
    with pytest.raises(ValueError, match="same project"):
        repository.add_dependency("t-1", "t-2")


def test_database_triggers_enforce_dependency_integrity_on_update(repository):
    repository.create_project("p-1", "One")
    repository.create_project("p-2", "Two")
    repository.create_task("t-1", "p-1", "One")
    repository.create_task("t-2", "p-1", "Two")
    repository.create_task("t-3", "p-2", "Three")
    repository.add_dependency("t-2", "t-1")

    with repository.database.connection() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="same project"):
            connection.execute(
                "UPDATE task_dependencies SET depends_on_task_id = ? WHERE task_id = ?",
                ("t-3", "t-2"),
            )
        with pytest.raises(sqlite3.IntegrityError, match="same project"):
            connection.execute(
                "UPDATE task_dependencies SET task_id = ? WHERE task_id = ?",
                ("t-3", "t-2"),
            )

    assert repository.list_dependencies("t-2") == ["t-1"]


def test_database_triggers_reject_dependency_cycles_on_insert_and_update(repository):
    repository.create_project("p-1", "One")
    for task_id in ("t-1", "t-2", "t-3"):
        repository.create_task(task_id, "p-1", task_id)

    repository.add_dependency("t-2", "t-1")
    repository.add_dependency("t-3", "t-2")

    with repository.database.connection() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="cycle"):
            connection.execute(
                "INSERT INTO task_dependencies(task_id, depends_on_task_id, created_at) "
                "VALUES (?, ?, ?)",
                ("t-1", "t-3", "2026-11-20T00:00:00+00:00"),
            )
        with pytest.raises(sqlite3.IntegrityError, match="cycle"):
            connection.execute(
                "UPDATE task_dependencies SET depends_on_task_id = ? WHERE task_id = ?",
                ("t-3", "t-2"),
            )

    assert repository.list_dependencies("t-2") == ["t-1"]
    assert repository.list_dependencies("t-3") == ["t-2"]


def test_activity_history_records_json_payload(repository):
    repository.create_project("p-1", "Demo")
    repository.create_task("t-1", "p-1", "Task")
    event_id = repository.record_activity("p-1", "task.created", task_id="t-1",
                                          payload={"status": "todo", "priority": "high"})
    event = repository.list_activity("p-1")[0]
    assert event["id"] == event_id
    assert event["payload"] == {"priority": "high", "status": "todo"}
    assert event["event_type"] == "task.created"


def test_activity_task_must_belong_to_same_project(repository):
    repository.create_project("p-1", "One")
    repository.create_project("p-2", "Two")
    repository.create_task("t-1", "p-1", "Task one")
    repository.create_task("t-2", "p-2", "Task two")

    with pytest.raises(ValueError, match="same project"):
        repository.record_activity("p-1", "task.updated", task_id="t-2")

    assert repository.list_activity("p-1") == []


def test_database_trigger_rejects_cross_project_activity_insert_and_update(repository):
    repository.create_project("p-1", "One")
    repository.create_project("p-2", "Two")
    repository.create_task("t-1", "p-1", "Task one")
    repository.create_task("t-2", "p-2", "Task two")

    with repository.database.connection() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="same project"):
            connection.execute(
                """INSERT INTO activity_history
                   (project_id, task_id, event_type, payload_json, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                ("p-1", "t-2", "task.updated", "{}", "2026-11-20T00:00:00+00:00"),
            )

    event_id = repository.record_activity("p-1", "task.created", task_id="t-1")
    with repository.database.connection() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="same project"):
            connection.execute(
                "UPDATE activity_history SET task_id = ? WHERE id = ?",
                ("t-2", event_id),
            )
        with pytest.raises(sqlite3.IntegrityError, match="same project"):
            connection.execute(
                "UPDATE activity_history SET project_id = ? WHERE id = ?",
                ("p-2", event_id),
            )


def test_delete_project_cascades_related_records(repository):
    repository.create_project("p-1", "Demo")
    repository.create_task("t-1", "p-1", "Task")
    repository.record_activity("p-1", "project.created")
    assert repository.delete_project("p-1") is True
    assert repository.list_projects() == []
