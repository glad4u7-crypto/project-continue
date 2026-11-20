import pytest

pytestmark = pytest.mark.integration
from database import Database,ProjectRepository
from services import ProjectManagementService,TaskManagementService

@pytest.fixture
def ws(tmp_path):
 db=Database(tmp_path/"tasks.db");repo=ProjectRepository(db);repo.initialize()
 p=ProjectManagementService(repo).create_project("Task workspace")
 return repo,TaskManagementService(repo),p["id"]

def test_create_assignment_priority_and_activity(ws):
 repo,s,pid=ws;t=s.create_task(pid,"Release",description="Checklist",assignee=" Alex ",priority="HIGH")
 assert (t["assignee"],t["priority"],t["status"])==("Alex","high","todo")
 assert repo.list_activity(pid)[0]["event_type"]=="task.created"

def test_validation_and_assignment_clear(ws):
 _,s,pid=ws
 with pytest.raises(KeyError):s.create_task("missing","Task")
 with pytest.raises(ValueError):s.create_task(pid," ")
 with pytest.raises(ValueError):s.create_task(pid,"Task",assignee="x"*121)
 t=s.create_task(pid,"Assigned",assignee="A");assert s.assign_task(t["id"],"B")["assignee"]=="B"
 assert s.assign_task(t["id"],None)["assignee"] is None

@pytest.mark.parametrize("value",["low","medium","high","critical"])
def test_priorities(ws,value):
 _,s,pid=ws;t=s.create_task(pid,"P");assert s.set_priority(t["id"],value)["priority"]==value

@pytest.mark.parametrize("value",["todo","in_progress","blocked","done"])
def test_statuses(ws,value):
 _,s,pid=ws;t=s.create_task(pid,"S");assert s.set_status(t["id"],value)["status"]==value

def test_invalid_priority(ws):
 _,s,pid=ws;t=s.create_task(pid,"P")
 with pytest.raises(ValueError):s.set_priority(t["id"],"urgent")

def test_update_and_activity(ws):
 repo,s,pid=ws;t=s.create_task(pid,"Old")
 u=s.update_task(t["id"],title="New",description="Updated",assignee="Team",priority="critical")
 assert (u["title"],u["description"],u["assignee"],u["priority"])==("New","Updated","Team","critical")
 assert repo.list_activity(pid)[0]["event_type"]=="task.updated"

def test_dependency_completion_gate_and_removal(ws):
 _,s,pid=ws;a=s.create_task(pid,"Prerequisite");b=s.create_task(pid,"Dependent")
 s.add_dependency(b["id"],a["id"]);assert not s.get_task_details(b["id"])["can_complete"]
 with pytest.raises(ValueError,match="Complete prerequisite"):s.complete_task(b["id"])
 s.complete_task(a["id"]);assert s.complete_task(b["id"])["status"]=="done"

def test_dependency_cycles_and_project_scope(ws):
 repo,s,pid=ws;a=s.create_task(pid,"A");b=s.create_task(pid,"B");s.add_dependency(a["id"],b["id"])
 with pytest.raises(ValueError,match="cycle"):s.add_dependency(b["id"],a["id"])
 other=ProjectManagementService(repo).create_project("Other");c=s.create_task(other["id"],"C")
 with pytest.raises(ValueError,match="same project"):s.add_dependency(a["id"],c["id"])

def test_filters_search_assignee(ws):
 _,s,pid=ws;s.create_task(pid,"Docs",assignee="Sam",priority="high");s.create_task(pid,"Bug",assignee="Riya",priority="low")
 assert [x["title"] for x in s.list_tasks(pid,priority="high",query="sam")]==["Docs"]

def test_v1_migration_preserves_rows(tmp_path):
 db=Database(tmp_path/"old.db")
 with db.connection() as c:
  c.executescript("""CREATE TABLE schema_version(id INTEGER PRIMARY KEY CHECK(id=1),version INTEGER NOT NULL);INSERT INTO schema_version VALUES(1,1);
  CREATE TABLE projects(id TEXT PRIMARY KEY,name TEXT NOT NULL UNIQUE,description TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'active',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
  CREATE TABLE tasks(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id),title TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',priority TEXT NOT NULL DEFAULT 'medium',status TEXT NOT NULL DEFAULT 'todo',due_at TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
  INSERT INTO projects VALUES('p','Legacy','','active','now','now');INSERT INTO tasks VALUES('t','p','Existing','','medium','todo',NULL,'now','now');""")
 repo=ProjectRepository(db);repo.initialize();assert repo.get_task("t")["assignee"] is None
 with db.connection() as c:assert c.execute("SELECT version FROM schema_version WHERE id=1").fetchone()["version"]==2

def test_delete_task_cascades_dependency_and_nulls_history(ws):
 repo,s,pid=ws;a=s.create_task(pid,"A");b=s.create_task(pid,"B");s.add_dependency(b["id"],a["id"]);repo.delete_task(a["id"])
 assert s.get_task_details(b["id"])["dependency_ids"]==[]
 assert any(e["event_type"]=="task.created" and e["task_id"] is None for e in repo.list_activity(pid))
