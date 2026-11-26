"""Phase 17 U01-U04 multi-agent manager acceptance tests."""
import pytest

from database import Database, ProjectRepository
from services.project_management import ProjectManagementService
from services.multi_agent_manager import AgentManagerError, MultiAgentManager


@pytest.fixture
def workspace(tmp_path):
    db = Database(tmp_path / "multi-agent.sqlite3")
    repo = ProjectRepository(db)
    repo.initialize()
    first = ProjectManagementService(repo).create_project("Agent workspace")
    second = ProjectManagementService(repo).create_project("Isolated workspace")
    manager = MultiAgentManager(repo)
    yield db, repo, manager, first["id"], second["id"]
    db.close()


def test_u01_registration_persists_agent_and_capabilities(workspace):
    _, _, manager, project_id, _ = workspace
    agent = manager.register_agent(project_id, "Researcher", description="Finds evidence",
                                   capabilities=["web.search", "summarize", "web.search"])
    assert agent["id"].startswith("agent-")
    assert agent["name"] == "Researcher"
    assert agent["description"] == "Finds evidence"
    assert agent["capabilities"] == ["summarize", "web.search"]
    assert agent["status"] == "active"
    assert manager.get_agent(project_id, agent["id"])["id"] == agent["id"]
    assert len(manager.list_agents(project_id)) == 1


def test_u01_rejects_invalid_and_duplicate_agents(workspace):
    _, _, manager, project_id, _ = workspace
    manager.register_agent(project_id, "Unique")
    with pytest.raises(AgentManagerError, match="already exists"):
        manager.register_agent(project_id, "Unique")
    with pytest.raises(AgentManagerError):
        manager.register_agent(project_id, " ")
    with pytest.raises(AgentManagerError):
        manager.register_agent(project_id, "Bad", capabilities=["invalid capability"])
    with pytest.raises(AgentManagerError):
        manager.register_agent(project_id, "Too many", capabilities=[f"cap{i}" for i in range(33)])


def test_u01_agents_are_isolated_by_project(workspace):
    _, _, manager, first, second = workspace
    agent = manager.register_agent(first, "Private")
    assert manager.get_agent(second, agent["id"]) is None
    assert manager.list_agents(second) == []


def test_u02_role_assignment_supports_multiple_roles_and_removal(workspace):
    _, _, manager, project_id, _ = workspace
    agent = manager.register_agent(project_id, "Coordinator")
    assigned = manager.assign_role(project_id, agent["id"], "coordinator")
    assigned = manager.assign_role(project_id, agent["id"], "reviewer")
    assert assigned["roles"] == ["coordinator", "reviewer"]
    assert manager.remove_role(project_id, agent["id"], "reviewer")
    assert manager.get_agent(project_id, agent["id"])["roles"] == ["coordinator"]
    assert not manager.remove_role(project_id, agent["id"], "reviewer")


def test_u02_rejects_unknown_role_and_missing_agent(workspace):
    _, _, manager, project_id, _ = workspace
    agent = manager.register_agent(project_id, "Planner")
    with pytest.raises(AgentManagerError):
        manager.assign_role(project_id, agent["id"], "root")
    with pytest.raises(KeyError):
        manager.assign_role(project_id, "missing", "planner")


def test_u03_selects_only_active_role_and_capability_match(workspace):
    _, _, manager, project_id, _ = workspace
    wrong = manager.register_agent(project_id, "Wrong capability", capabilities=["summarize"])
    right = manager.register_agent(project_id, "Right capability", capabilities=["web.search", "summarize"])
    manager.assign_role(project_id, wrong["id"], "researcher")
    manager.assign_role(project_id, right["id"], "researcher")
    selected = manager.select_agent(project_id, "researcher", required_capabilities=["web.search"])
    assert selected["id"] == right["id"]
    assert selected["selection_count"] == 1


def test_u03_least_used_selection_balances_matching_agents(workspace):
    _, _, manager, project_id, _ = workspace
    first = manager.register_agent(project_id, "A")
    second = manager.register_agent(project_id, "B")
    for agent in (first, second):
        manager.assign_role(project_id, agent["id"], "executor")
    selected = [manager.select_agent(project_id, "executor")["id"] for _ in range(4)]
    assert selected.count(first["id"]) == 2
    assert selected.count(second["id"]) == 2


def test_u03_disabled_agents_are_not_selected(workspace):
    _, _, manager, project_id, _ = workspace
    agent = manager.register_agent(project_id, "Paused")
    manager.assign_role(project_id, agent["id"], "monitor")
    assert manager.set_agent_status(project_id, agent["id"], "disabled")
    assert manager.list_agents(project_id) == []
    assert manager.select_agent(project_id, "monitor") is None
    assert manager.list_agents(project_id, include_disabled=True)[0]["status"] == "disabled"


def test_u04_agent_message_send_inbox_and_read_receipt(workspace):
    _, _, manager, project_id, _ = workspace
    sender = manager.register_agent(project_id, "Sender")
    receiver = manager.register_agent(project_id, "Receiver")
    message = manager.send_message(project_id, sender["id"], receiver["id"],
                                   {"task_id": "task-1", "instruction": "Review output"},
                                   message_type="request")
    assert message["status"] == "queued"
    assert message["payload"]["instruction"] == "Review output"
    assert manager.list_messages(project_id, receiver["id"])[0]["id"] == message["id"]
    assert manager.mark_message_read(project_id, receiver["id"], message["id"])
    assert not manager.mark_message_read(project_id, receiver["id"], message["id"])
    assert manager.list_messages(project_id, receiver["id"], unread_only=True) == []
    assert manager.list_messages(project_id, sender["id"], inbox=False)[0]["id"] == message["id"]


def test_u04_rejects_self_cross_project_disabled_and_invalid_messages(workspace):
    _, _, manager, first, second = workspace
    sender = manager.register_agent(first, "Sender")
    receiver = manager.register_agent(first, "Receiver")
    foreign = manager.register_agent(second, "Foreign")
    with pytest.raises(AgentManagerError):
        manager.send_message(first, sender["id"], sender["id"], {})
    with pytest.raises(AgentManagerError):
        manager.send_message(first, sender["id"], foreign["id"], {})
    with pytest.raises(AgentManagerError):
        manager.send_message(first, sender["id"], receiver["id"], {"bad": object()})
    with pytest.raises(AgentManagerError):
        manager.send_message(first, sender["id"], receiver["id"], {"blob": "x" * 17000})
    with pytest.raises(AgentManagerError):
        manager.send_message(first, sender["id"], receiver["id"], [], message_type="request")
    manager.set_agent_status(first, receiver["id"], "disabled")
    with pytest.raises(AgentManagerError):
        manager.send_message(first, sender["id"], receiver["id"], {})


def test_u04_message_access_is_project_scoped(workspace):
    _, _, manager, first, second = workspace
    sender = manager.register_agent(first, "Sender")
    receiver = manager.register_agent(first, "Receiver")
    message = manager.send_message(first, sender["id"], receiver["id"], {"ok": True})
    assert manager.get_message(second, message["id"]) is None
    assert manager.list_messages(second, receiver["id"]) == []
    assert not manager.mark_message_read(second, receiver["id"], message["id"])


def test_role_selection_and_communication_validation(workspace):
    _, _, manager, project_id, _ = workspace
    with pytest.raises(AgentManagerError):
        manager.select_agent(project_id, "superuser")
    with pytest.raises(AgentManagerError):
        manager.list_messages(project_id, "missing", limit=201)
    agent = manager.register_agent(project_id, "Agent")
    with pytest.raises(AgentManagerError):
        manager.set_agent_status(project_id, agent["id"], "deleted")
