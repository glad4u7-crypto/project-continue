"""Cross-database application-service acceptance for PostgreSQL."""
from __future__ import annotations
import os
import uuid
import pytest
from database.postgres_connection import PostgresDatabase
from database.postgres_repository import PostgresProjectRepository
from services.access_control import AccessDenied
from services.authorization import ProjectAuthorization
from services.authorization_context import AuthorizationContext
from services.automation_engine import AutomationEngine
from services.memory_checkpoint_engine import MemoryCheckpointEngine
from services.multi_agent_manager import MultiAgentManager
from services.project_management import ProjectManagementService
from services.postgres_access_control import PostgresAccessControl
from services.task_management import TaskManagementService

pytestmark = pytest.mark.integration

@pytest.fixture
def postgres_workspace():
    dsn = os.getenv("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("TEST_POSTGRES_DSN is not configured")
    suffix = uuid.uuid4().hex[:12]
    database = PostgresDatabase(dsn)
    repository = PostgresProjectRepository(database)
    repository.initialize()
    project_id = f"svc-{suffix}"
    repository.create_project(project_id, f"Service compatibility {suffix}")
    # Ensure global automation tables exist before the fixture cleanup path.
    AutomationEngine(repository)
    try:
        yield database, repository, project_id, suffix
    finally:
        with database.transaction() as connection:
            connection.execute(
                "DELETE FROM automation_runs WHERE schedule_id IN "
                "(SELECT id FROM automation_schedules WHERE name = %s)",
                (f"svc-{suffix}",),
            )
            connection.execute("DELETE FROM automation_schedules WHERE name = %s", (f"svc-{suffix}",))
            connection.execute("DELETE FROM projects WHERE id = %s", (project_id,))
            connection.execute("DELETE FROM pc_users WHERE id LIKE %s", (f"svc-{suffix}-%",))

def test_project_and_task_services_run_unchanged_on_postgres(postgres_workspace):
    _database, repository, project_id, _suffix = postgres_workspace
    projects = ProjectManagementService(repository)
    tasks = TaskManagementService(repository)
    project = projects.get_project_details(project_id)
    assert project is not None and project["name"].startswith("Service compatibility")
    updated = projects.update_project(project_id, description="PostgreSQL service path")
    assert updated["description"] == "PostgreSQL service path"
    prerequisite = tasks.create_task(project_id, "Prerequisite")
    dependent = tasks.create_task(project_id, "Dependent", priority="high")
    tasks.add_dependency(dependent["id"], prerequisite["id"])
    assert tasks.get_task_details(dependent["id"])["can_complete"] is False
    tasks.complete_task(prerequisite["id"])
    assert tasks.complete_task(dependent["id"])["status"] == "done"
    assert tasks.list_tasks(project_id, status="done")
    assert projects.get_project_details(project_id)["completed_tasks"] == 2
    assert repository.list_activity(project_id)

def test_memory_checkpoint_service_runs_on_postgres(postgres_workspace):
    _database, repository, project_id, _suffix = postgres_workspace
    tasks = TaskManagementService(repository)
    task = tasks.create_task(project_id, "Snapshot task")
    memory = MemoryCheckpointEngine(repository)
    assert memory.remember(project_id, "storage", "postgresql", kind="constraint")["value"] == "postgresql"
    memory.record_session(project_id, "pause", "Service acceptance checkpoint")
    decision = memory.record_decision(project_id, "Database", "Compatibility", "PostgreSQL", "Shared service SQL adapter")
    checkpoint = memory.create_checkpoint(project_id, "Service checkpoint", checkpoint_id=f"svc-checkpoint-{_suffix}")
    assert memory.get_memory(project_id, "storage")["value"] == "postgresql"
    assert memory.list_sessions(project_id)[0]["summary"] == "Service acceptance checkpoint"
    assert memory.get_decision(decision["decision_id"])["decision"] == "PostgreSQL"
    assert memory.get_checkpoint(checkpoint["checkpoint_id"])["payload"]["tasks"][0]["id"] == task["id"]
    assert memory.recover_state(checkpoint["checkpoint_id"])["verified"] is True
    assert "Project Handoff" in memory.generate_handoff(project_id)

def test_automation_service_runs_on_postgres(postgres_workspace):
    _database, repository, project_id, suffix = postgres_workspace
    engine = AutomationEngine(repository)
    tasks = TaskManagementService(repository)
    engine.create_task_status_rule(project_id, "done")
    task = tasks.create_task(project_id, "Automated task")
    tasks.complete_task(task["id"])
    notifications = engine.list_notifications(unread_only=True)
    assert any(item["project_id"] == project_id and item["kind"] == "task_status" for item in notifications)
    schedule_id = engine.create_schedule(f"svc-{suffix}", "database_health", interval_seconds=60)
    assert engine.run_due_checks()["succeeded"] >= 1
    assert engine.set_schedule_enabled(schedule_id, False)
    assert engine.list_schedules()

def test_authentication_and_authorization_services_run_on_postgres(postgres_workspace):
    database, repository, project_id, suffix = postgres_workspace
    access = PostgresAccessControl(database, "service-test-signing-key-" + ("x" * 40))
    user_id = f"svc-{suffix}-owner"
    email = f"{user_id}@example.test"
    access.create_user(user_id, email, "Service-test-password-123!", role="owner")
    principal = access.authenticate(email, "Service-test-password-123!")
    assert principal is not None
    token = access.issue_session(principal)
    verified = access.verify_session(token)
    assert verified is not None
    access.bootstrap_project_owner(verified, project_id)
    context = AuthorizationContext(ProjectAuthorization(access), verified)
    projects = ProjectManagementService(repository, context)
    tasks = TaskManagementService(repository, context)
    assert projects.get_project_details(project_id)["id"] == project_id
    created = tasks.create_task(project_id, "Authorized task")
    assert created["title"] == "Authorized task"
    viewer_id = f"svc-{suffix}-viewer"
    access.create_user(viewer_id, f"{viewer_id}@example.test", "Service-test-password-123!", role="viewer")
    viewer = access.authenticate(f"{viewer_id}@example.test", "Service-test-password-123!")
    assert viewer is not None
    access.grant_project(verified, project_id, viewer_id, role="viewer")
    viewer_context = AuthorizationContext(ProjectAuthorization(access), viewer)
    with pytest.raises(AccessDenied):
        TaskManagementService(repository, viewer_context).create_task(project_id, "Must be denied")


def test_multi_agent_manager_runs_on_postgres(postgres_workspace):
    _database, repository, project_id, _suffix = postgres_workspace
    manager = MultiAgentManager(repository)
    researcher = manager.register_agent(
        project_id, "Postgres researcher", capabilities=["search", "summarize"]
    )
    reviewer = manager.register_agent(project_id, "Postgres reviewer", capabilities=["review"])
    manager.assign_role(project_id, researcher["id"], "researcher")
    manager.assign_role(project_id, reviewer["id"], "reviewer")
    selected = manager.select_agent(
        project_id, "researcher", required_capabilities=["search"]
    )
    assert selected["id"] == researcher["id"]
    message = manager.send_message(
        project_id, researcher["id"], reviewer["id"],
        {"finding": "verified"}, message_type="handoff",
    )
    assert manager.list_messages(project_id, reviewer["id"])[0]["id"] == message["id"]
    assert manager.mark_message_read(project_id, reviewer["id"], message["id"])
    assert manager.get_message(project_id, message["id"])["status"] == "read"
