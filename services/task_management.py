"""Task management workflows."""
from __future__ import annotations
import logging
import sqlite3,uuid
from typing import Any
from core.validation import validate_task_title
from database.repository import ProjectRepository
from services.authorization_context import AuthorizationContext, requires_project

_LOG=logging.getLogger(__name__)
class TaskManagementService:
 def __init__(self,repository:ProjectRepository,authorization_context:AuthorizationContext|None=None)->None:self.repository=repository;self.authorization_context=authorization_context
 @staticmethod
 def _description(v:str)->str:
  if not isinstance(v,str):raise ValueError("Task description must be text")
  v=v.strip()
  if len(v)>4000:raise ValueError("Task description must be 4000 characters or fewer")
  return v
 @staticmethod
 def _assignee(v:str|None)->str|None:
  if v is None:return None
  if not isinstance(v,str):raise ValueError("Assignee must be text")
  v=v.strip()
  if len(v)>120:raise ValueError("Assignee must be 120 characters or fewer")
  return v or None
 @staticmethod
 def _due(v:str|None)->str|None:
  if v in (None,""):return None
  if not isinstance(v,str) or len(v)>40:raise ValueError("Due date must be a valid date or timestamp")
  return v
 @requires_project("write", project_arg="project_id")
 def create_task(self,project_id:str,title:str,*,description:str="",assignee:str|None=None,priority:str="medium",status:str="todo",due_at:str|None=None,task_id:str|None=None)->dict[str,Any]:
  if self.repository.get_project(project_id) is None:raise KeyError(project_id)
  title=validate_task_title(title);description=self._description(description);assignee=self._assignee(assignee);due_at=self._due(due_at);tid=task_id or f"tsk-{uuid.uuid4().hex[:12]}"
  try:t=self.repository.create_task(tid,project_id,title,description=description,assignee=assignee,priority=priority,status=status,due_at=due_at)
  except sqlite3.IntegrityError as e:raise ValueError("Task data violates a database constraint") from e
  self.repository.record_activity(project_id,"task.created",task_id=tid,payload={"title":title,"priority":t["priority"],"status":t["status"]})
  return self.get_task_details(tid)
 @requires_project("read", resource_arg="task_id", resolver="get_task")
 def get_task_details(self,task_id:str)->dict[str,Any]:
  t=self.repository.get_task(task_id)
  if t is None:raise KeyError(task_id)
  deps=[self.repository.get_task(i) for i in self.repository.list_dependencies(task_id)];deps=[d for d in deps if d]
  pending=[d for d in deps if d["status"]!="done"]
  return {**t,"dependencies":deps,"dependency_ids":[d["id"] for d in deps],"pending_dependencies":pending,"can_complete":not pending}
 @requires_project("read", project_arg="project_id")
 def list_tasks(self,project_id:str,*,status:str="all",priority:str="all",query:str="")->list[dict[str,Any]]:
  if self.repository.get_project(project_id) is None:raise KeyError(project_id)
  if status not in {"all","todo","in_progress","blocked","done"}:raise ValueError("Unsupported task status filter")
  if priority not in {"all","low","medium","high","critical"}:raise ValueError("Unsupported task priority filter")
  q=query.strip().casefold();out=[]
  for t in self.repository.list_tasks(project_id):
   if status!="all" and t["status"]!=status:continue
   if priority!="all" and t["priority"]!=priority:continue
   if q not in " ".join((t["title"],t["description"],t["assignee"] or "")).casefold():continue
   out.append(self.get_task_details(t["id"]))
  return out
 @requires_project("write", resource_arg="task_id", resolver="get_task")
 def update_task(self,task_id:str,*,title:str|None=None,description:str|None=None,assignee:str|None=None,priority:str|None=None,status:str|None=None,due_at:str|None=None)->dict[str,Any]:
  old=self.repository.get_task(task_id)
  if old is None:raise KeyError(task_id)
  f={}
  if title is not None:f["title"]=validate_task_title(title)
  if description is not None:f["description"]=self._description(description)
  if assignee is not None:f["assignee"]=self._assignee(assignee) or ""
  if priority is not None:f["priority"]=priority
  if status is not None:f["status"]=status
  if due_at is not None:f["due_at"]=self._due(due_at) or ""
  if not f:return self.get_task_details(task_id)
  if f.get("status")=="done":self._assert_dependencies_complete(task_id)
  new=self.repository.update_task(task_id,**f)
  self.repository.record_activity(old["project_id"],"task.updated",task_id=task_id,payload={"fields":sorted(f)})
  if old["status"]!="done" and new["status"]=="done":self.repository.record_activity(old["project_id"],"task.completed",task_id=task_id)
  if old["status"]!=new["status"]:
   try:
    from services.automation_engine import AutomationEngine
    AutomationEngine(self.repository).handle_task_update(old,new)
   except Exception:
    _LOG.exception("Task update automation failed; task update remains committed")
  return self.get_task_details(task_id)
 def assign_task(self,task_id:str,assignee:str|None)->dict[str,Any]:
  result=self.update_task(task_id,assignee=assignee if assignee is not None else "")
  self.repository.record_activity(result["project_id"],"task.assigned",task_id=task_id,payload={"assignee":result["assignee"]});return result
 def set_priority(self,task_id:str,priority:str)->dict[str,Any]:return self.update_task(task_id,priority=priority)
 def set_status(self,task_id:str,status:str)->dict[str,Any]:return self.update_task(task_id,status=status)
 def _assert_dependencies_complete(self,task_id:str)->None:
  pending=self.get_task_details(task_id)["pending_dependencies"]
  if pending:raise ValueError("Complete prerequisite task(s) first: "+", ".join(x["title"] for x in pending))
 def complete_task(self,task_id:str)->dict[str,Any]:
  self._assert_dependencies_complete(task_id);t=self.repository.get_task(task_id)
  if t is None:raise KeyError(task_id)
  return self.get_task_details(task_id) if t["status"]=="done" else self.set_status(task_id,"done")
 @requires_project("write", resource_arg="task_id", resolver="get_task")
 def add_dependency(self,task_id:str,depends_on_task_id:str)->dict[str,Any]:
  self.repository.add_dependency(task_id,depends_on_task_id);t=self.repository.get_task(task_id)
  self.repository.record_activity(t["project_id"],"task.dependency_added",task_id=task_id,payload={"depends_on_task_id":depends_on_task_id});return self.get_task_details(task_id)
 @requires_project("write", resource_arg="task_id", resolver="get_task")
 def remove_dependency(self,task_id:str,depends_on_task_id:str)->dict[str,Any]:
  t=self.repository.get_task(task_id)
  if t is None:raise KeyError(task_id)
  if self.repository.remove_dependency(task_id,depends_on_task_id):self.repository.record_activity(t["project_id"],"task.dependency_removed",task_id=task_id,payload={"depends_on_task_id":depends_on_task_id})
  return self.get_task_details(task_id)
