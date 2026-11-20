"""Deterministic decision support for project tasks."""
from __future__ import annotations
from datetime import date, datetime, time, timezone
from typing import Any, Iterable, Mapping

_STATUS_ORDER = {"in_progress": 0, "todo": 1, "blocked": 2, "done": 3}
_PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
_PRIORITY_POINTS = {"critical": 40, "high": 30, "medium": 20, "low": 10}
_MISSING_DATE = datetime.max.replace(tzinfo=timezone.utc)


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime): parsed = value
    elif isinstance(value, date): parsed = datetime.combine(value, time.min)
    elif isinstance(value, str) and value.strip():
        raw = value.strip()
        try: parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            try: parsed = datetime.combine(date.fromisoformat(raw), time.min)
            except ValueError: return _MISSING_DATE
    else: return _MISSING_DATE
    if parsed.tzinfo is None: parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class IntelligentTaskEngine:
    """Read-only, deterministic decision engine over repository task records."""
    def __init__(self, repository: Any) -> None: self.repository = repository

    @staticmethod
    def rank_tasks(tasks: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        prepared = []
        for task in tasks:
            if not isinstance(task, Mapping): raise ValueError("Each task must be a mapping")
            item = dict(task); task_id = item.get("id")
            if not isinstance(task_id, str) or not task_id.strip(): raise ValueError("Each task must have a non-empty string id")
            status = str(item.get("status") or "").strip().lower()
            priority = str(item.get("priority") or "").strip().lower()
            due, created = _parse_timestamp(item.get("due_at")), _parse_timestamp(item.get("created_at"))
            reasons = {"in_progress":["Already in progress"],"todo":["Ready to start"],"blocked":["Blocked"],"done":["Already completed"]}.get(status,["Unknown status"])
            reasons = list(reasons) + ([f"{priority.title()} priority"] if priority in _PRIORITY_ORDER else ["Unknown priority"])
            reasons += [f"Due {due.date().isoformat()}" if due != _MISSING_DATE else "No valid due date"]
            key = (_STATUS_ORDER.get(status,4),_PRIORITY_ORDER.get(priority,4),due,created,task_id.casefold(),task_id)
            prepared.append((key,item,reasons))
        prepared.sort(key=lambda x:x[0])
        result=[]
        for rank,(_,item,reasons) in enumerate(prepared,1):
            item["rank"]=rank; item["ranking_reason"]=reasons; result.append(item)
        return result

    def rank_project_tasks(self, project_id: str) -> list[dict[str, Any]]:
        if self.repository.get_project(project_id) is None: raise KeyError(project_id)
        return self.rank_tasks(self.repository.list_tasks(project_id))

    def analyze_dependencies(self, task_id: str) -> dict[str, Any]:
        task=self.repository.get_task(task_id)
        if task is None: raise KeyError(task_id)
        visited=set(); visiting=set(); ordered=[]; cycle=False
        def visit(current):
            nonlocal cycle
            if current in visiting: cycle=True; return
            if current in visited: return
            visiting.add(current)
            for dep_id in self.repository.list_dependencies(current):
                dep=self.repository.get_task(dep_id)
                if dep is None: continue
                if dep_id in visiting: cycle=True; continue
                visit(dep_id)
                if dep_id not in {x["id"] for x in ordered}: ordered.append(dep)
            visiting.remove(current); visited.add(current)
        visit(task_id)
        pending=[x for x in ordered if x["status"]!="done"]
        return {"task_id":task_id,"dependencies":ordered,"direct_dependency_ids":sorted(self.repository.list_dependencies(task_id)),"pending_dependencies":pending,"ready":not pending and not cycle,"has_cycle":cycle,"dependency_count":len(ordered)}

    def calculate_priority(self, task: Mapping[str, Any], *, as_of: Any = None) -> dict[str, Any]:
        if not isinstance(task,Mapping) or not isinstance(task.get("id"),str) or not task["id"].strip(): raise ValueError("A task mapping with a non-empty id is required")
        priority=str(task.get("priority") or "medium").lower(); status=str(task.get("status") or "todo").lower()
        score=_PRIORITY_POINTS.get(priority,10); reasons=[f"Base priority: {priority} (+{score})"]
        if status=="done": return {"task_id":task["id"],"score":0,"reasons":["Task already completed"],"priority":priority}
        if status=="in_progress": score+=15; reasons.append("Work already in progress (+15)")
        elif status=="todo": score+=10; reasons.append("Ready-to-start task (+10)")
        elif status=="blocked": score-=20; reasons.append("Blocked (-20)")
        due=_parse_timestamp(task.get("due_at")); reference=_parse_timestamp(as_of) if as_of is not None else datetime.now(timezone.utc)
        if due!=_MISSING_DATE:
            days=(due.date()-reference.date()).days
            bonus=30 if days<0 else 25 if days<=1 else 20 if days<=3 else 12 if days<=7 else 6 if days<=14 else 0
            if bonus: score+=bonus; reasons.append(f"Due urgency (+{bonus})")
        else: reasons.append("No valid due date (+0)")
        return {"task_id":task["id"],"score":max(0,min(100,score)),"reasons":reasons,"priority":priority}

    def calculate_project_priorities(self, project_id: str, *, as_of: Any = None) -> list[dict[str, Any]]:
        if self.repository.get_project(project_id) is None: raise KeyError(project_id)
        rows=[]
        for task in self.repository.list_tasks(project_id):
            result=self.calculate_priority(task,as_of=as_of); result["task"]=dict(task); rows.append(result)
        return sorted(rows,key=lambda x:(-x["score"],x["task_id"]))

    def detect_blocked_tasks(self, project_id: str) -> list[dict[str, Any]]:
        if self.repository.get_project(project_id) is None: raise KeyError(project_id)
        result=[]
        for task in self.repository.list_tasks(project_id):
            analysis=self.analyze_dependencies(task["id"])
            if task["status"]=="blocked" or analysis["pending_dependencies"] or analysis["has_cycle"]:
                reason="Explicitly marked blocked" if task["status"]=="blocked" else "Dependency cycle detected" if analysis["has_cycle"] else "Unfinished prerequisite tasks"
                result.append({"task":dict(task),"blocked":True,"reason":reason,"pending_dependencies":analysis["pending_dependencies"]})
        return result

    def select_next_task(self, project_id: str, *, as_of: Any = None) -> dict[str, Any] | None:
        if self.repository.get_project(project_id) is None: raise KeyError(project_id)
        candidates=[]
        for task in self.repository.list_tasks(project_id):
            if task["status"] not in {"todo","in_progress"} or not self.analyze_dependencies(task["id"])["ready"]: continue
            score=self.calculate_priority(task,as_of=as_of)
            candidates.append((-score["score"],task["id"],task,score))
        if not candidates: return None
        _,_,task,score=min(candidates,key=lambda x:(x[0],x[1]))
        return {**dict(task),"priority_score":score["score"],"selection_reason":score["reasons"]}

    def recommend_actions(self, project_id: str, *, as_of: Any = None, limit: int = 5) -> list[dict[str, Any]]:
        if not isinstance(limit,int) or isinstance(limit,bool) or limit<1: raise ValueError("limit must be a positive integer")
        if self.repository.get_project(project_id) is None: raise KeyError(project_id)
        result=[]
        for task in self.repository.list_tasks(project_id):
            if task["status"]=="done": continue
            analysis=self.analyze_dependencies(task["id"])
            if task["status"]=="blocked" or not analysis["ready"]: action,reason="unblock","Resolve prerequisite tasks before starting"
            elif task["status"]=="in_progress": action,reason="continue","Continue the task already in progress"
            else: action,reason="start","Task is ready and has no unfinished prerequisites"
            result.append({"task_id":task["id"],"action":action,"reason":reason,"priority_score":self.calculate_priority(task,as_of=as_of)["score"]})
        return sorted(result,key=lambda x:(-x["priority_score"],x["task_id"]))[:limit]

    def verify_completion(self, task_id: str) -> dict[str, Any]:
        task=self.repository.get_task(task_id)
        if task is None: raise KeyError(task_id)
        analysis=self.analyze_dependencies(task_id); errors=[]
        if task["status"]!="done": errors.append("Task status is not done")
        if analysis["pending_dependencies"]: errors.append("One or more prerequisite tasks are not complete")
        if analysis["has_cycle"]: errors.append("Dependency cycle detected")
        return {"task_id":task_id,"verified":not errors,"status":task["status"],"errors":errors,"pending_dependency_ids":[x["id"] for x in analysis["pending_dependencies"]]}
