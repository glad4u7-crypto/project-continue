"""Migration dry-run and opt-in live migration acceptance tests."""
from __future__ import annotations

import os

import pytest

from database.connection import Database
from database.repository import ProjectRepository
from database.postgres_migration import migrate_sqlite_to_postgres
from services.access_control import AccessControl


def _make_source_database(path):
    database = Database(path)
    repository = ProjectRepository(database)
    repository.initialize()
    project = repository.create_project("migration-project", "Migration fixture")
    repository.create_task("migration-task-1", project["id"], "First task")
    repository.create_task("migration-task-2", project["id"], "Second task")
    repository.add_dependency("migration-task-2", "migration-task-1")
    repository.record_activity(project["id"], "migration.fixture",
                               task_id="migration-task-1",
                               payload={"verified": True})

    access = AccessControl(database, "migration-test-signing-key-" + ("x" * 40))
    access.create_user("migration-owner", "migration-owner@example.test",
                       "Migration-test-password-123!", role="owner")
    principal = access.authenticate("migration-owner@example.test",
                                    "Migration-test-password-123!")
    assert principal is not None
    access.bootstrap_project_owner(principal, project["id"])
    access.require_project(principal, project["id"], permission="write")
    return database


def test_sqlite_to_postgres_migration_dry_run_is_read_only(tmp_path):
    source_path = tmp_path / "source.sqlite3"
    source = _make_source_database(source_path)
    try:
        report = migrate_sqlite_to_postgres(
            source_path, "postgresql://not-used-in-dry-run", dry_run=True
        )
        assert report["dry_run"] is True
        assert report["source_schema_version"] == 2
        assert report["target_schema_version"] == 2
        assert report["tables"]["projects"]["rows"] == 1
        assert report["tables"]["tasks"]["rows"] == 2
        assert report["tables"]["pc_users"]["rows"] == 1
        assert report["tables"]["pc_project_memberships"]["rows"] == 1
        assert report["tables"]["pc_audit_events"]["rows"] >= 1
        assert len(report["tables"]["projects"]["sha256"]) == 64
    finally:
        source.close()


@pytest.mark.integration
def test_sqlite_to_postgres_migration_verifies_all_rows(tmp_path):
    dsn = os.getenv("TEST_POSTGRES_MIGRATION_DSN")
    if not dsn:
        pytest.skip("TEST_POSTGRES_MIGRATION_DSN is not configured")

    source_path = tmp_path / "source.sqlite3"
    source = _make_source_database(source_path)
    try:
        report = migrate_sqlite_to_postgres(source_path, dsn, dry_run=False)
        assert report["migrated"] is True
        assert report["verified"] is True
        assert report["tables"]["projects"]["rows"] == 1
        assert report["tables"]["tasks"]["rows"] == 2
    finally:
        source.close()
