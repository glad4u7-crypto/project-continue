from types import SimpleNamespace

import pytest

from database import Database, ProjectRepository
from services.access_control import AccessControl
from scripts import manage_access


@pytest.fixture
def provisioned_db(tmp_path, monkeypatch):
    path = tmp_path / "access.sqlite3"
    key = "test-signing-key-" * 4
    db = Database(path)
    repo = ProjectRepository(db)
    repo.initialize()
    repo.create_project("project-1", "Project One")
    access = AccessControl(db, key)
    access.create_user("admin-1", "admin@example.test", "admin-password-123", role="admin")
    access.create_user("editor-1", "editor@example.test", "editor-password-123", role="editor")
    db.close()

    monkeypatch.setattr(manage_access, "get_settings", lambda: SimpleNamespace(database_path=str(path)))
    monkeypatch.setenv("SESSION_SIGNING_KEY", key)
    return path


def test_cli_bootstraps_owner_and_grants_membership(provisioned_db, monkeypatch, capsys):
    answers = iter(["admin-password-123", "admin-password-123", "admin-password-123", "viewer-password-123", "viewer-password-123"])
    monkeypatch.setattr(manage_access.getpass, "getpass", lambda _prompt: next(answers))

    assert manage_access.main([
        "--admin-email", "admin@example.test", "bootstrap-owner", "--project-id", "project-1"
    ]) == 0
    assert manage_access.main([
        "--admin-email", "admin@example.test", "grant-project",
        "--project-id", "project-1", "--email", "editor@example.test", "--role", "editor"
    ]) == 0
    assert manage_access.main([
        "--admin-email", "admin@example.test", "create-user",
        "--email", "viewer@example.test", "--role", "viewer"
    ]) == 0

    db = Database(provisioned_db)
    with db.connection() as connection:
        memberships = connection.execute(
            "SELECT user_id,role FROM pc_project_memberships WHERE project_id='project-1' ORDER BY user_id"
        ).fetchall()
        users = connection.execute(
            "SELECT email,role FROM pc_users ORDER BY email"
        ).fetchall()
    db.close()

    assert {(row["user_id"], row["role"]) for row in memberships} == {
        ("admin-1", "owner"), ("editor-1", "editor")
    }
    assert [(row["email"], row["role"]) for row in users] == [
        ("admin@example.test", "admin"),
        ("editor@example.test", "editor"),
        ("viewer@example.test", "viewer"),
    ]
    output = capsys.readouterr().out
    assert "PROJECT OWNER BOOTSTRAPPED" in output
    assert "PROJECT MEMBERSHIP SET" in output
    assert "USER CREATED" in output
    assert "viewer-password-123" not in output


def test_cli_rejects_non_admin_and_password_mismatch(provisioned_db, monkeypatch, capsys):
    monkeypatch.setattr(manage_access.getpass, "getpass", lambda _prompt: "editor-password-123")
    assert manage_access.main([
        "--admin-email", "editor@example.test", "list-users"
    ]) == 1
    assert "PermissionError" in capsys.readouterr().err

    answers = iter(["admin-password-123", "first-password-123", "different-password-123"])
    monkeypatch.setattr(manage_access.getpass, "getpass", lambda _prompt: next(answers))
    assert manage_access.main([
        "--admin-email", "admin@example.test", "create-user", "--email", "new@example.test"
    ]) == 1
    assert "ValueError" in capsys.readouterr().err

    db = Database(provisioned_db)
    with db.connection() as connection:
        count = connection.execute("SELECT COUNT(*) AS n FROM pc_users").fetchone()["n"]
    db.close()
    assert count == 2
