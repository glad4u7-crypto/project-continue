"""Validated SQLite project and task repository."""
from __future__ import annotations
import json
from datetime import datetime,timezone
from typing import Any
from core.validation import validate_identifier,validate_priority,validate_project_name,validate_task_status,validate_task_title
from database.connection import Database
from database.schema import SCHEMA_SQL,SCHEMA_VERSION

def _now()->str: return datetime.now(timezone.utc).isoformat()

class ProjectRepository:
 def __init__(self,database:Database)->None: self.database=database
 def initialize(self)->None:
  """Apply schema creation and migrations atomically under a write lock.

  BEGIN IMMEDIATE serializes concurrent app workers before they inspect or
  change the schema, preventing duplicate/racing migration attempts.
  """
  with self.database.connection() as c:
   try:
    c.executescript("BEGIN IMMEDIATE;\n" + SCHEMA_SQL)
    cols={r["name"] for r in c.execute("PRAGMA table_info(tasks)")}
    if "assignee" not in cols:
     c.execute("ALTER TABLE tasks ADD COLUMN assignee TEXT")
    v=c.execute("SELECT version FROM schema_version WHERE id=1").fetchone()
    if v is None or v["version"]>SCHEMA_VERSION:
     raise RuntimeError("Database schema version is newer than this application supports")
    c.execute("UPDATE schema_version SET version=? WHERE id=1",(SCHEMA_VERSION,))
    c.commit()
   except BaseException:
    if c.in_transaction:
     c.rollback()
    raise
 def create_project(self,project_id:str,name:str,description:str="")->dict[str,Any]:
  project_id,name=validate_identifier(project_id),validate_project_name(name); now=_now()
  with self.database.transaction() as c: c.execute("INSERT INTO projects(id,name,description,created_at,updated_at) VALUES(?,?,?,?,?)",(project_id,name,description,now,now))
  return self.get_project(project_id)
 def get_project(self,project_id:str)->dict[str,Any]|None:
  with self.database.connection() as c:
   r=c.execute("SELECT * FROM projects WHERE id=?",(validate_identifier(project_id),)).fetchone(); return dict(r) if r else None
 def list_projects(self)->list[dict[str,Any]]:
  with self.database.connection() as c: return [dict(r) for r in c.execute("SELECT * FROM projects ORDER BY created_at,id")]
 def update_project(self,project_id:str,*,name:str|None=None,description:str|None=None,status:str|None=None)->dict[str,Any]:
  project_id=validate_identifier(project_id); f={}
  if name is not None:f["name"]=validate_project_name(name)
  if description is not None:f["description"]=description
  if status is not None:
   status=status.strip().lower()
   if status not in {"active","archived"}:raise ValueError("Project status must be active or archived")
   f["status"]=status
  if not f:
   p=self.get_project(project_id)
   if p is None:raise KeyError(project_id)
   return p
  f["updated_at"]=_now(); sql=",".join(f"{k}=?" for k in f)
  with self.database.transaction() as c:
   cur=c.execute(f"UPDATE projects SET {sql} WHERE id=? ",(*f.values(),project_id))
   if not cur.rowcount:raise KeyError(project_id)
  return self.get_project(project_id)
 def delete_project(self,project_id:str)->bool:
  with self.database.transaction() as c:return c.execute("DELETE FROM projects WHERE id=?",(validate_identifier(project_id),)).rowcount>0
 def create_task(self,task_id:str,project_id:str,title:str,*,description:str="",assignee:str|None=None,priority:str="medium",status:str="todo",due_at:str|None=None)->dict[str,Any]:
  task_id,project_id=validate_identifier(task_id),validate_identifier(project_id); title=validate_task_title(title); priority=validate_priority(priority); status=validate_task_status(status); now=_now()
  with self.database.transaction() as c:c.execute("INSERT INTO tasks(id,project_id,title,description,assignee,priority,status,due_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(task_id,project_id,title,description,assignee,priority,status,due_at,now,now))
  return self.get_task(task_id)
 def get_task(self,task_id:str)->dict[str,Any]|None:
  with self.database.connection() as c:
   r=c.execute("SELECT * FROM tasks WHERE id=?",(validate_identifier(task_id),)).fetchone();return dict(r) if r else None
 def list_tasks(self,project_id:str)->list[dict[str,Any]]:
  with self.database.connection() as c:return [dict(r) for r in c.execute("SELECT * FROM tasks WHERE project_id=? ORDER BY created_at,id",(validate_identifier(project_id),))]
 def update_task(self,task_id:str,*,title:str|None=None,description:str|None=None,assignee:str|None=None,priority:str|None=None,status:str|None=None,due_at:str|None=None)->dict[str,Any]:
  task_id=validate_identifier(task_id);f={}
  if title is not None:f["title"]=validate_task_title(title)
  if description is not None:f["description"]=description
  if assignee is not None:f["assignee"]=assignee.strip() or None
  if priority is not None:f["priority"]=validate_priority(priority)
  if status is not None:f["status"]=validate_task_status(status)
  if due_at is not None:f["due_at"]=due_at
  if not f:
   t=self.get_task(task_id)
   if t is None:raise KeyError(task_id)
   return t
  f["updated_at"]=_now();sql=",".join(f"{k}=?" for k in f)
  with self.database.transaction() as c:
   cur=c.execute(f"UPDATE tasks SET {sql} WHERE id=? ",(*f.values(),task_id))
   if not cur.rowcount:raise KeyError(task_id)
  return self.get_task(task_id)
 def delete_task(self,task_id:str)->bool:
  with self.database.transaction() as c:return c.execute("DELETE FROM tasks WHERE id=?",(validate_identifier(task_id),)).rowcount>0
 def add_dependency(self,task_id:str,depends_on_task_id:str)->None:
  task_id,depends_on_task_id=validate_identifier(task_id),validate_identifier(depends_on_task_id)
  if task_id==depends_on_task_id:raise ValueError("A task cannot depend on itself")
  with self.database.transaction() as c:
   rows=c.execute("SELECT id,project_id FROM tasks WHERE id IN (?,?)",(task_id,depends_on_task_id)).fetchall()
   if len(rows)!=2:raise KeyError("Both tasks must exist")
   if len({r["project_id"] for r in rows})!=1:raise ValueError("Task dependencies must belong to the same project")
   cycle=c.execute("WITH RECURSIVE r(id) AS (SELECT depends_on_task_id FROM task_dependencies WHERE task_id=? UNION SELECT d.depends_on_task_id FROM task_dependencies d JOIN r ON d.task_id=r.id) SELECT 1 FROM r WHERE id=? LIMIT 1",(depends_on_task_id,task_id)).fetchone()
   if cycle:raise ValueError("Dependency would create a cycle")
   c.execute("INSERT INTO task_dependencies VALUES(?,?,?)",(task_id,depends_on_task_id,_now()))
 def remove_dependency(self,task_id:str,depends_on_task_id:str)->bool:
  with self.database.transaction() as c:return c.execute("DELETE FROM task_dependencies WHERE task_id=? AND depends_on_task_id=?",(validate_identifier(task_id),validate_identifier(depends_on_task_id))).rowcount>0
 def list_dependencies(self,task_id:str)->list[str]:
  with self.database.connection() as c:return [r["depends_on_task_id"] for r in c.execute("SELECT depends_on_task_id FROM task_dependencies WHERE task_id=? ORDER BY depends_on_task_id",(validate_identifier(task_id),))]
 def record_activity(self,project_id:str,event_type:str,*,task_id:str|None=None,payload:dict[str,Any]|None=None)->int:
  project_id=validate_identifier(project_id)
  if not isinstance(event_type,str) or not event_type.strip():raise ValueError("event_type must be non-empty text")
  data=json.dumps(payload or {},sort_keys=True,separators=(",",":"))
  with self.database.transaction() as c:
   if task_id is not None:
    task_id=validate_identifier(task_id);t=c.execute("SELECT project_id FROM tasks WHERE id=?",(task_id,)).fetchone()
    if t is None:raise KeyError(task_id)
    if t["project_id"]!=project_id:raise ValueError("Activity task must belong to the same project")
   cur=c.execute("INSERT INTO activity_history(project_id,task_id,event_type,payload_json,created_at) VALUES(?,?,?,?,?)",(project_id,task_id,event_type.strip(),data,_now()));return int(cur.lastrowid)
 def list_activity(self,project_id:str,*,limit:int=100)->list[dict[str,Any]]:
  if not 1<=limit<=1000:raise ValueError("limit must be between 1 and 1000")
  with self.database.connection() as c:
   result=[]
   for r in c.execute("SELECT * FROM activity_history WHERE project_id=? ORDER BY id DESC LIMIT ?",(validate_identifier(project_id),limit)):
    item=dict(r);item["payload"]=json.loads(item.pop("payload_json"));result.append(item)
   return result
