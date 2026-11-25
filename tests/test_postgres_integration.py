"""Opt-in live PostgreSQL acceptance tests.

Set TEST_POSTGRES_DSN to a dedicated disposable PostgreSQL database.
These tests never fall back to or touch the application's SQLite database.
"""
from __future__ import annotations

import os
import uuid

import pytest

from database.postgres_repository import PostgresProjectRepository
from database.postgres_connection import PostgresDatabase
from services.access_control import AccessDenied
from services.postgres_access_control import PostgresAccessControl


pytestmark = pytest.mark.integration


@pytest.fixture
def postgres_env():
    dsn = os.getenv("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("TEST_POSTGRES_DSN is not configured; live PostgreSQL tests are opt-in")

    psycopg = pytest.importorskip("psycopg")
    database = PostgresDatabase(dsn)
    repository = PostgresProjectRepository(database)
    repository.initialize()
    repository.initialize()  # initializer must be idempotent

    suffix = uuid.uuid4().hex[:12]
    project_id = f"pgtest-{suffix}"
    other_project_id = f"pgtest-other-{suffix}"
    repository.create_project(project_id, f"PG integration {suffix}")
    repository.create_project(other_project_id, f"PG integration other {suffix}")

    try:
        yield database, repository, project_id, other_project_id, suffix, psycopg
    finally:
        # The DSN is explicitly required to point at a disposable test database.
        with database.transaction() as connection:
            connection.execute("DELETE FROM projects WHERE id = %s", (project_id,))
            connection.execute("DELETE FROM projects WHERE id = %s", (other_project_id,))
            connection.execute("DELETE FROM pc_users WHERE id LIKE %s", (f"pgtest-{suffix}-%",))


def test_postgres_repository_crud_dependencies_and_database_guards(postgres_env):
    database, repo, project_id, other_project_id, suffix, psycopg = postgres_env
    repo.create_task(f"pgtest-{suffix}-a", project_id, "Task A")
    repo.create_task(f"pgtest-{suffix}-b", project_id, "Task B")
    repo.create_task(f"pgtest-{suffix}-c", project_id, "Task C")
    repo.add_dependency(f"pgtest-{suffix}-a", f"pgtest-{suffix}-b")
    repo.add_dependency(f"pgtest-{suffix}-b", f"pgtest-{suffix}-c")
    assert repo.list_dependencies(f"pgtest-{suffix}-a") == [f"pgtest-{suffix}-b"]
    with pytest.raises(ValueError, match="cycle"):
        repo.add_dependency(f"pgtest-{suffix}-c", f"pgtest-{suffix}-a")

    repo.record_activity(project_id, "integration.test", task_id=f"pgtest-{suffix}-a",
                         payload={"source": "pytest"})
    activity = repo.list_activity(project_id)
    assert activity[0]["payload"] == {"source": "pytest"}

    with pytest.raises(ValueError, match="same project"):
        repo.record_activity(other_project_id, "invalid.cross-project",
                             task_id=f"pgtest-{suffix}-a")

    # Exercise the database trigger directly, bypassing repository validation.
    with pytest.raises(psycopg.errors.RaiseException, match="same project"):
        with database.transaction() as connection:
            connection.execute(
                "INSERT INTO task_dependencies(task_id, depends_on_task_id, created_at) "
                "VALUES (%s, %s, %s)",
                (f"pgtest-{suffix}-a", f"pgtest-{suffix}-c", "test"),
            )


def test_postgres_access_control_sessions_membership_and_immutable_audit(postgres_env):
    database, repo, project_id, _other_project_id, suffix, psycopg = postgres_env
    access = PostgresAccessControl(database, "test-signing-key-" + ("x" * 40))
    owner_id = f"pgtest-{suffix}-owner"
    editor_id = f"pgtest-{suffix}-editor"
    viewer_id = f"pgtest-{suffix}-viewer"
    password = "Test-only-password-123!"

    access.create_user(owner_id, f"{owner_id}@example.test", password, role="owner")
    owner = access.authenticate(f"{owner_id}@example.test", password)
    assert owner is not None
    token = access.issue_session(owner)
    verified_owner = access.verify_session(token)
    assert verified_owner is not None and verified_owner["id"] == owner_id

    access.bootstrap_project_owner(verified_owner, project_id)
    access.require_project(verified_owner, project_id, permission="write")

    access.create_user(editor_id, f"{editor_id}@example.test", password, role="editor")
    editor = access.authenticate(f"{editor_id}@example.test", password)
    assert editor is not None
    access.grant_project(verified_owner, project_id, editor_id, role="editor")
    access.require_project(editor, project_id, permission="write")

    access.create_user(viewer_id, f"{viewer_id}@example.test", password, role="viewer")
    viewer = access.authenticate(f"{viewer_id}@example.test", password)
    assert viewer is not None
    access.grant_project(verified_owner, project_id, viewer_id, role="viewer")
    access.require_project(viewer, project_id, permission="read")
    with pytest.raises(AccessDenied):
        access.require_project(viewer, project_id, permission="write")

    events = access.list_audit_events(limit=100)
    assert events
    with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
        with database.transaction() as connection:
            connection.execute(
                "UPDATE pc_audit_events SET outcome = 'tampered' WHERE id = %s",
                (events[0]["id"],),
            )
