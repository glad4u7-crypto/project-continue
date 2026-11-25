"""Unit and opt-in live tests for PostgreSQL backup/restore safety."""
from __future__ import annotations

import json
import os
import shutil
import uuid

import pytest

from database.postgres_backup import (
    create_postgres_backup,
    restore_postgres_backup,
    verify_postgres_backup,
)
from database.postgres_connection import PostgresDatabase
from database.postgres_repository import PostgresProjectRepository


def test_backup_verification_detects_tampering(tmp_path, monkeypatch):
    import database.postgres_backup as backup

    archive = tmp_path / "sample.dump"
    archive.write_bytes(b"valid-archive")
    manifest = archive.with_name(archive.name + ".manifest.json")
    manifest.write_text(json.dumps({
        "format": "postgresql-custom",
        "archive": archive.name,
        "size_bytes": archive.stat().st_size,
        "sha256": backup._sha256(archive),
    }), encoding="utf-8")
    monkeypatch.setattr(backup, "_tool", lambda _name: "/bin/true")
    assert verify_postgres_backup(archive)["archive"] == archive.name
    archive.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="size|SHA-256"):
        verify_postgres_backup(archive)


def test_restore_refuses_nonempty_target_before_pg_restore(tmp_path, monkeypatch):
    import database.postgres_backup as backup

    archive = tmp_path / "not-used.dump"
    archive.write_bytes(b"archive")
    manifest = archive.with_name(archive.name + ".manifest.json")
    manifest.write_text(json.dumps({
        "format": "postgresql-custom", "archive": archive.name,
        "size_bytes": archive.stat().st_size, "sha256": backup._sha256(archive),
    }), encoding="utf-8")
    monkeypatch.setattr(backup, "_tool", lambda _name: "/bin/true")
    monkeypatch.setattr(backup, "_database_is_empty", lambda _dsn: False)
    with pytest.raises(RuntimeError, match="not empty"):
        restore_postgres_backup(archive, "postgresql://unused")


@pytest.mark.integration
def test_postgres_backup_restore_round_trip(tmp_path):
    source_dsn = os.getenv("TEST_POSTGRES_BACKUP_DSN")
    target_dsn = os.getenv("TEST_POSTGRES_RESTORE_DSN")
    if not source_dsn or not target_dsn:
        pytest.skip("Dedicated TEST_POSTGRES_BACKUP_DSN and TEST_POSTGRES_RESTORE_DSN are required")
    if not shutil.which("pg_dump") or not shutil.which("pg_restore"):
        pytest.skip("PostgreSQL client tools are not installed")

    source = PostgresDatabase(source_dsn)
    repo = PostgresProjectRepository(source)
    repo.initialize()
    suffix = uuid.uuid4().hex[:10]
    project_id = f"backup-{suffix}"
    repo.create_project(project_id, f"Backup restore {suffix}")
    repo.create_task(f"backup-task-{suffix}", project_id, "Backup test task")

    archive = tmp_path / f"project-continue-{suffix}.dump"
    try:
        created = create_postgres_backup(source_dsn, archive)
        assert created["sha256"] == verify_postgres_backup(archive)["sha256"]
        restored = restore_postgres_backup(archive, target_dsn)
        assert restored["restored"] is True
        assert restored["verified"] is True
        with PostgresDatabase(target_dsn).connection() as connection:
            row = connection.execute("SELECT name FROM projects WHERE id = %s", (project_id,)).fetchone()
            assert row and row["name"] == f"Backup restore {suffix}"
    finally:
        with source.transaction() as connection:
            connection.execute("DELETE FROM projects WHERE id = %s", (project_id,))
