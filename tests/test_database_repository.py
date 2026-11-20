import sqlite3

import pytest

pytestmark = pytest.mark.database

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


def test_file_backed_repository_persists_after_reopen(tmp_path):
    database_path = tmp_path / "durable" / "project.db"

    first_database = Database(database_path)
    first_repository = ProjectRepository(first_database)
    first_repository.initialize()
    first_repository.create_project("persist-project", "Persistent project")
    first_repository.create_task("persist-task-1", "persist-project", "First task")
    first_repository.create_task("persist-task-2", "persist-project", "Second task")
    first_repository.add_dependency("persist-task-2", "persist-task-1")
    first_repository.record_activity(
        "persist-project", "task.created", task_id="persist-task-1",
        payload={"source": "file-backed-reopen"},
    )
    first_database.close()

    reopened_database = Database(database_path)
    reopened_repository = ProjectRepository(reopened_database)
    try:
        reopened_repository.initialize()
        assert reopened_repository.get_project("persist-project")["name"] == "Persistent project"
        assert reopened_repository.get_task("persist-task-1")["title"] == "First task"
        assert reopened_repository.list_dependencies("persist-task-2") == ["persist-task-1"]
        events = reopened_repository.list_activity("persist-project")
        assert events[0]["payload"] == {"source": "file-backed-reopen"}
    finally:
        reopened_database.close()


def test_database_backup_can_be_restored_as_a_working_repository(tmp_path):
    source_path = tmp_path / "source" / "project.db"
    backup_path = tmp_path / "backup" / "project-backup.db"

    source_database = Database(source_path)
    source_repository = ProjectRepository(source_database)
    source_repository.initialize()
    source_repository.create_project("backup-project", "Backup project")
    source_repository.create_task("backup-task", "backup-project", "Restore me")
    source_repository.record_activity(
        "backup-project", "backup.created", task_id="backup-task",
        payload={"verified": True},
    )

    source_database.backup(backup_path)
    assert Database.verify_backup(backup_path) is True
    source_database.close()

    restored_database = Database(backup_path)
    restored_repository = ProjectRepository(restored_database)
    try:
        restored_repository.initialize()
        assert restored_repository.get_project("backup-project")["name"] == "Backup project"
        assert restored_repository.get_task("backup-task")["title"] == "Restore me"
        assert restored_repository.list_activity("backup-project")[0]["payload"] == {"verified": True}
    finally:
        restored_database.close()
