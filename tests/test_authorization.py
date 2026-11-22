"""Service-boundary authorization policy tests using isolated SQLite."""
import pytest

from database import Database, ProjectRepository
from services.access_control import AccessControl, AccessDenied
from services.authorization import ProjectAuthorization
from services.project_management import ProjectManagementService
from services.task_management import TaskManagementService
from services.authorization_context import AuthorizationContext
from services.memory_checkpoint_engine import MemoryCheckpointEngine
from services.automation_engine import AutomationEngine
from services.ai_brain import AIBrain, MockAIProvider
from services.intelligent_task_engine import IntelligentTaskEngine


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


def test_service_boundaries_enforce_owner_editor_viewer_and_project_isolation(secured):
    db, _, policy, principals, first, second = secured
    repo = ProjectRepository(db)
    owner = AuthorizationContext(policy, principals["owner"])
    editor = AuthorizationContext(policy, principals["editor"])
    viewer = AuthorizationContext(policy, principals["viewer"])
    outsider = AuthorizationContext(policy, principals["outsider"])

    owner_projects = ProjectManagementService(repo, owner)
    created = owner_projects.create_project("Owner-created project")
    assert created["id"] in {p["id"] for p in owner_projects.list_projects()}
    assert created["id"] not in {p["id"] for p in ProjectManagementService(repo, outsider).list_projects()}

    owner_tasks = TaskManagementService(repo, owner)
    task = owner_tasks.create_task(first, "Authorized task")
    assert TaskManagementService(repo, viewer).get_task_details(task["id"])["id"] == task["id"]
    TaskManagementService(repo, editor).update_task(task["id"], title="Editor update")
    with pytest.raises(AccessDenied):
        TaskManagementService(repo, viewer).update_task(task["id"], title="Viewer update")
    with pytest.raises(AccessDenied):
        TaskManagementService(repo, outsider).get_task_details(task["id"])
    with pytest.raises(AccessDenied):
        TaskManagementService(repo, editor).list_tasks(second)


def test_memory_checkpoint_and_recovery_are_project_scoped(secured):
    db, _, policy, principals, first, second = secured
    repo = ProjectRepository(db)
    owner = AuthorizationContext(policy, principals["owner"])
    viewer = AuthorizationContext(policy, principals["viewer"])
    outsider = AuthorizationContext(policy, principals["outsider"])
    owner_engine = MemoryCheckpointEngine(repo, authorization_context=owner)
    owner_engine.remember(first, "goal", "ship safely")
    checkpoint = owner_engine.create_checkpoint(first, "before-recovery")

    viewer_engine = MemoryCheckpointEngine(repo, authorization_context=viewer)
    assert viewer_engine.get_checkpoint(checkpoint["checkpoint_id"])["project_id"] == first
    with pytest.raises(AccessDenied):
        viewer_engine.remember(first, "forbidden", "no")
    with pytest.raises(AccessDenied):
        viewer_engine.recover_state(checkpoint["checkpoint_id"], apply=True)
    with pytest.raises(AccessDenied):
        MemoryCheckpointEngine(repo, authorization_context=outsider).get_checkpoint(checkpoint["checkpoint_id"])
    with pytest.raises(AccessDenied):
        owner_engine.list_memory(second)


def test_ai_approval_is_project_scoped_and_requester_bound(secured):
    db, _, policy, principals, first, _ = secured
    repo = ProjectRepository(db)
    owner = AuthorizationContext(policy, principals["owner"])
    editor = AuthorizationContext(policy, principals["editor"])
    viewer = AuthorizationContext(policy, principals["viewer"])
    brain = AIBrain(repo, IntelligentTaskEngine(repo), MockAIProvider(), authorization_context=owner)
    result = brain.suggest(first)
    with pytest.raises(AccessDenied):
        brain.approvals.decide(result["approval_request_id"], approved=True)

    editor_brain = AIBrain(repo, IntelligentTaskEngine(repo), MockAIProvider(), authorization_context=editor)
    editor_result = editor_brain.suggest(first)
    with pytest.raises(AccessDenied):
        editor_brain.approvals.decide(editor_result["approval_request_id"], approved=True)
    with pytest.raises(AccessDenied):
        AIBrain(repo, IntelligentTaskEngine(repo), MockAIProvider(), authorization_context=viewer).approvals.decide(
            result["approval_request_id"], approved=True
        )
    assert brain.approvals.decide(result["approval_request_id"], approved=True).status == "approved"


def test_automation_global_controls_are_admin_only_and_notifications_are_scoped(secured):
    db, _, policy, principals, first, second = secured
    repo = ProjectRepository(db)
    owner = AuthorizationContext(policy, principals["owner"])
    viewer = AuthorizationContext(policy, principals["viewer"])
    admin_engine = AutomationEngine(repo)
    admin_engine.notify(first, "system", "First project", "Visible to members")
    admin_engine.notify(second, "system", "Second project", "Not visible to first-project members")
    member_engine = AutomationEngine(repo, authorization_context=viewer)
    assert [n["title"] for n in member_engine.list_notifications()] == ["First project"]
    with pytest.raises(AccessDenied):
        member_engine.create_schedule("forbidden", "database_health")
    with pytest.raises(AccessDenied):
        member_engine.list_schedules()
    assert AutomationEngine(repo, authorization_context=owner).create_task_status_rule(first, "done")


def test_principal_id_cannot_be_forged_to_impersonate_owner(secured):
    _, _, policy, _, first, _ = secured
    forged = {"id": "owner", "email": "owner@example.test", "role": "owner"}
    with pytest.raises(AccessDenied):
        policy.require_read(forged, first)
    with pytest.raises(AccessDenied):
        AuthorizationContext(policy, forged)
