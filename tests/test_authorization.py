"""Service-boundary authorization policy tests using isolated SQLite."""
import pytest

from database import Database, ProjectRepository
from services.access_control import AccessControl, AccessDenied
from services.authorization import ProjectAuthorization
from services.project_management import ProjectManagementService


@pytest.fixture
def secured(tmp_path):
    db = Database(tmp_path / "authorization.db")
    repo = ProjectRepository(db)
    repo.initialize()
    projects = ProjectManagementService(repo)
    first = projects.create_project("First")
    second = projects.create_project("Second")
    access = AccessControl(db, b"x" * 32)
    access.create_user("owner", "owner@example.test", "owner-password-123", role="owner")
    access.create_user("editor", "editor@example.test", "editor-password-123", role="editor")
    access.create_user("viewer", "viewer@example.test", "viewer-password-123", role="viewer")
    access.create_user("outsider", "outsider@example.test", "outsider-password-123", role="viewer")
    principals = {
        uid: access.authenticate(email, password)
        for uid, email, password in (
            ("owner", "owner@example.test", "owner-password-123"),
            ("editor", "editor@example.test", "editor-password-123"),
            ("viewer", "viewer@example.test", "viewer-password-123"),
            ("outsider", "outsider@example.test", "outsider-password-123"),
        )
    }
    access.bootstrap_project_owner(principals["owner"], first["id"])
    access.grant_project(principals["owner"], first["id"], "editor", role="editor")
    access.grant_project(principals["owner"], first["id"], "viewer", role="viewer")
    policy = ProjectAuthorization(access)
    yield db, access, policy, principals, first["id"], second["id"]
    db.close()


def test_owner_editor_viewer_and_nonmember_permissions(secured):
    _, _, policy, p, first, second = secured
    policy.require_read(p["owner"], first)
    policy.require_write(p["owner"], first)
    policy.require_manage(p["owner"], first)
    policy.require_read(p["editor"], first)
    policy.require_write(p["editor"], first)
    with pytest.raises(AccessDenied):
        policy.require_manage(p["editor"], first)
    policy.require_read(p["viewer"], first)
    with pytest.raises(AccessDenied):
        policy.require_write(p["viewer"], first)
    with pytest.raises(AccessDenied):
        policy.require_read(p["outsider"], first)
    for principal in p.values():
        with pytest.raises(AccessDenied):
            policy.require_read(principal, second)


def test_missing_or_forged_principal_fails_closed(secured):
    _, _, policy, _, first, _ = secured
    for principal in (None, {}, {"role": "admin"}, {"id": ""}):
        with pytest.raises(AccessDenied):
            policy.require_read(principal, first)


def test_resource_scope_comes_from_canonical_resource(secured):
    _, _, policy, p, first, second = secured
    resource = {"id": "task-1", "project_id": first}
    assert policy.require_resource_write(p["editor"], resource) == first
    with pytest.raises(AccessDenied):
        policy.require_resource_write(p["viewer"], resource)
    # Missing project scope is treated as not found, not as global access.
    with pytest.raises(AccessDenied, match="Resource not found"):
        policy.require_resource_read(p["owner"], {"id": "orphan"})
    # A different canonical project scope is never overridden by caller intent.
    with pytest.raises(AccessDenied):
        policy.require_resource_read(p["owner"], {"id": "task-2", "project_id": second})


def test_disabled_account_is_denied_after_authentication(secured):
    _, access, policy, p, first, _ = secured
    with access.database.transaction() as c:
        c.execute("UPDATE pc_users SET enabled=0 WHERE id='editor'")
    with pytest.raises(AccessDenied):
        policy.require_write(p["editor"], first)
