"""Phase 13 memory/checkpoint engine tests using isolated SQLite databases."""
import pytest
from database import Database, ProjectRepository
from services.project_management import ProjectManagementService
from services.memory_checkpoint_engine import MemoryCheckpointEngine, MemoryCheckpointError

@pytest.fixture
def workspace(tmp_path):
    db=Database(tmp_path/"memory.db");repo=ProjectRepository(db);repo.initialize()
    project=ProjectManagementService(repo).create_project("Memory Test")
    engine=MemoryCheckpointEngine(repo)
    yield db,repo,engine,project["id"]
    db.close()

def test_memory_schema_upsert_and_scope(workspace):
    _,_,e,pid=workspace
    assert e.remember(pid,"runtime",{"environment":"colab"},kind="constraint")["value"]["environment"]=="colab"
    e.remember(pid,"runtime",{"environment":"local"},kind="fact")
    assert len(e.list_memory(pid))==1 and e.get_memory(pid,"runtime")["value"]["environment"]=="local"
    assert e.forget_memory(pid,"runtime")

def test_memory_validation(workspace):
    _,_,e,pid=workspace
    with pytest.raises(MemoryCheckpointError):e.remember(pid,"x","secret",kind="unknown")
    with pytest.raises(MemoryCheckpointError):e.remember(pid,"x","a"*13000)

def test_checkpoint_snapshot_and_integrity(workspace):
    _,repo,e,pid=workspace
    repo.create_task("task-one",pid,"First task")
    cp=e.create_checkpoint(pid,"Before change",checkpoint_id="PC-P13-TEST-001")
    assert cp["payload"]["tasks"][0]["id"]=="task-one"
    assert e.get_checkpoint("PC-P13-TEST-001")["payload_sha256"]==cp["payload_sha256"]
    assert e.list_checkpoints(pid)[0]["checkpoint_id"]=="PC-P13-TEST-001"

def test_session_history_is_durable(workspace):
    _,_,e,pid=workspace
    event=e.record_session(pid,"pause","Stopped after tests",session_id="session-1",metadata={"checkpoint":"PC-P13-TEST-001"})
    assert event["session_id"]=="session-1"
    assert e.list_sessions(pid)[0]["metadata"]["checkpoint"]=="PC-P13-TEST-001"

def test_decision_records(workspace):
    _,_,e,pid=workspace
    item=e.record_decision(pid,"Use SQLite","Need durable local state","SQLite","Already part of stack")
    assert item["status"]=="accepted" and e.get_decision(item["decision_id"])["decision"]=="SQLite"
    assert e.list_decisions(pid)[0]["title"]=="Use SQLite"

def test_handoff_contains_resume_context(workspace):
    _,_,e,pid=workspace
    e.remember(pid,"environment","Colab",kind="constraint")
    e.record_session(pid,"pause","Phase 13 tests")
    e.record_decision(pid,"Storage","Durability","SQLite","Local-first")
    handoff=e.generate_handoff(pid)
    assert "Project Handoff" in handoff and "Colab" in handoff and "Local-first" in handoff

def test_resume_parser_allowlist(workspace):
    _,_,e,_=workspace
    assert e.parse_resume_command("resume cp-123")=={"command":"resume","argument":"cp-123"}
    assert e.parse_resume_command("status")["command"]=="status"
    with pytest.raises(MemoryCheckpointError):e.parse_resume_command("run rm -rf /")
    with pytest.raises(MemoryCheckpointError):e.parse_resume_command("resume")

def test_recovery_preview_and_additive_restore(workspace):
    _,repo,e,pid=workspace
    repo.create_task("restore-me",pid,"Snapshot task")
    repo.create_task("keep-me",pid,"Original title")
    cp=e.create_checkpoint(pid,"Recovery source",checkpoint_id="PC-P13-RECOVER-001")
    repo.update_task("keep-me",title="Changed live title")
    repo.delete_task("restore-me")
    preview=e.recover_state(cp["checkpoint_id"])
    assert preview["verified"] and preview["missing_task_ids"]==["restore-me"] and repo.get_task("restore-me") is None
    applied=e.recover_state(cp["checkpoint_id"],apply=True)
    assert applied["restored_task_ids"]==["restore-me"] and repo.get_task("restore-me")["title"]=="Snapshot task"
    assert repo.get_task("keep-me")["title"]=="Changed live title"
    again=e.recover_state(cp["checkpoint_id"],apply=True)
    assert again["restored_task_ids"]==[] and again["skipped_existing_count"]==2

def test_resume_command_returns_verified_checkpoint(workspace):
    _,_,e,pid=workspace
    cp=e.create_checkpoint(pid,"Resume here",checkpoint_id="PC-P13-RESUME-001")
    result=e.resume("resume PC-P13-RESUME-001")
    assert result["recovery_preview"]["verified"] and result["checkpoint"]["checkpoint_id"]==cp["checkpoint_id"]


def test_checkpoint_corruption_is_rejected(workspace):
    db,_,engine,pid=workspace
    cp=engine.create_checkpoint(pid,"Integrity source",checkpoint_id="PC-P13-TAMPER-001")
    with db.transaction() as c:
        c.execute("UPDATE project_checkpoints SET payload_json=? WHERE checkpoint_id=?",
                  ('{"schema_version":1,"tasks":[]}',cp["checkpoint_id"]))
    with pytest.raises(MemoryCheckpointError):
        engine.get_checkpoint(cp["checkpoint_id"])


def test_checkpoint_operations_are_scoped_to_the_selected_project(workspace):
    _, repo, engine, project_id = workspace
    other = ProjectManagementService(repo).create_project("Other memory project")
    checkpoint = engine.create_checkpoint(
        project_id, "Private snapshot", checkpoint_id="PC-P13-SCOPE-001"
    )

    # A checkpoint ID cannot be used through a different selected project.
    assert engine.get_checkpoint(checkpoint["checkpoint_id"], project_id=other["id"]) is None
    with pytest.raises(KeyError):
        engine.recover_state(checkpoint["checkpoint_id"], project_id=other["id"])
    with pytest.raises(KeyError):
        engine.resume("resume PC-P13-SCOPE-001", project_id=other["id"])

    # The owning project can still inspect and preview the same checkpoint.
    assert engine.get_checkpoint(
        checkpoint["checkpoint_id"], project_id=project_id
    )["project_id"] == project_id
    assert engine.recover_state(
        checkpoint["checkpoint_id"], project_id=project_id
    )["verified"]
