"""Durable project memory, checkpoints, session history and safe resume/recovery."""
from __future__ import annotations
import hashlib, json, uuid
from typing import Any, Mapping
from datetime import datetime, timezone
from services.authorization_context import AuthorizationContext, requires_project
from services.access_control import AccessDenied

def _now(): return datetime.now(timezone.utc).isoformat()
def _json(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)

class MemoryCheckpointError(ValueError): pass

class MemoryCheckpointEngine:
    """SQLite continuity layer. Recovery is additive and never overwrites live records."""
    MEMORY_KINDS=frozenset({"preference","fact","constraint","decision","progress"})
    RESUME_VERBS=frozenset({"resume","status","handoff","checkpoint","help"})
    def __init__(self, repository: Any, clock=_now, authorization_context: AuthorizationContext | None = None):
        self.repository,self.db,self.clock=repository,repository.database,clock
        self.authorization_context=authorization_context
        with self.db.connection() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS project_memory(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,memory_key TEXT NOT NULL,kind TEXT NOT NULL,value_json TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(project_id,memory_key));
            CREATE TABLE IF NOT EXISTS project_checkpoints(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,checkpoint_id TEXT NOT NULL UNIQUE,label TEXT NOT NULL,schema_version INTEGER NOT NULL,payload_json TEXT NOT NULL,payload_sha256 TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_project_checkpoints ON project_checkpoints(project_id,created_at);
            CREATE TABLE IF NOT EXISTS session_history(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,session_id TEXT NOT NULL,event_type TEXT NOT NULL,summary TEXT NOT NULL,metadata_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_session_history ON session_history(project_id,created_at);
            CREATE TABLE IF NOT EXISTS decision_records(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,decision_id TEXT NOT NULL UNIQUE,title TEXT NOT NULL,context TEXT NOT NULL,decision TEXT NOT NULL,rationale TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            """)
    @staticmethod
    def _id(prefix): return prefix+"-"+uuid.uuid4().hex[:16]
    @staticmethod
    def _text(value,name,maximum=2000):
        if not isinstance(value,str) or not value.strip() or len(value.strip())>maximum: raise MemoryCheckpointError(f"{name} must contain 1-{maximum} characters")
        return value.strip()
    def _require_project(self,pid):
        project=self.repository.get_project(pid)
        if project is None: raise KeyError(pid)
        return project
    # PC-P13-S001
    @requires_project("write", project_arg="pid")
    def remember(self,pid,memory_key,value,*,kind="fact"): 
        self._require_project(pid); key=self._text(memory_key,"memory_key",120)
        if kind not in self.MEMORY_KINDS: raise MemoryCheckpointError("Unsupported memory kind")
        encoded=_json(value)
        if len(encoded)>12000: raise MemoryCheckpointError("Memory value exceeds 12000 characters")
        now=self.clock()
        with self.db.transaction() as c:
            c.execute("""INSERT INTO project_memory(id,project_id,memory_key,kind,value_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(project_id,memory_key) DO UPDATE SET kind=excluded.kind,value_json=excluded.value_json,updated_at=excluded.updated_at""",
            (self._id("mem"),pid,key,kind,encoded,now,now))
        return self.get_memory(pid,key)
    @requires_project("read", project_arg="pid")
    def get_memory(self,pid,key):
        with self.db.connection() as c: row=c.execute("SELECT * FROM project_memory WHERE project_id=? AND memory_key=?",(pid,key)).fetchone()
        if row is None:return None
        item=dict(row);item["value"]=json.loads(item.pop("value_json"));return item
    @requires_project("read", project_arg="pid")
    def list_memory(self,pid,*,kind=None):
        self._require_project(pid)
        if kind is not None and kind not in self.MEMORY_KINDS: raise MemoryCheckpointError("Unsupported memory kind")
        sql="SELECT * FROM project_memory WHERE project_id=?";args=(pid,)
        if kind:sql+=" AND kind=?";args+=(kind,)
        with self.db.connection() as c: rows=c.execute(sql+" ORDER BY memory_key",args).fetchall()
        result=[]
        for row in rows:
            item=dict(row);item["value"]=json.loads(item.pop("value_json"));result.append(item)
        return result
    @requires_project("write", project_arg="pid")
    def forget_memory(self,pid,key):
        with self.db.transaction() as c:return c.execute("DELETE FROM project_memory WHERE project_id=? AND memory_key=?",(pid,key)).rowcount==1
    # PC-P13-S002
    @requires_project("write", project_arg="pid")
    def create_checkpoint(self,pid,label,*,checkpoint_id=None):
        project=self._require_project(pid);label=self._text(label,"label",160);tasks=self.repository.list_tasks(pid)
        ids={t["id"] for t in tasks}
        deps=[{"task_id":tid,"depends_on_task_id":dep} for tid in sorted(ids) for dep in self.repository.list_dependencies(tid) if dep in ids]
        payload={"schema_version":1,"project":project,"tasks":tasks,"dependencies":deps};raw=_json(payload)
        digest=hashlib.sha256(raw.encode()).hexdigest();cid=self._text(checkpoint_id,"checkpoint_id",100) if checkpoint_id else self._id("PC13")
        with self.db.transaction() as c:
            c.execute("INSERT INTO project_checkpoints(id,project_id,checkpoint_id,label,schema_version,payload_json,payload_sha256,created_at) VALUES(?,?,?,?,1,?,?,?)",
                      (self._id("cp"),pid,cid,label,raw,digest,self.clock()))
        return self.get_checkpoint(cid)
    @requires_project("read", resource_arg="cid", resolver="get_checkpoint")
    def get_checkpoint(self,cid,*,project_id=None):
        with self.db.connection() as c:
            if project_id is None:
                row=c.execute("SELECT * FROM project_checkpoints WHERE checkpoint_id=?",(cid,)).fetchone()
            else:
                row=c.execute("SELECT * FROM project_checkpoints WHERE checkpoint_id=? AND project_id=?",(cid,project_id)).fetchone()
        if row is None:return None
        item=dict(row);raw=item["payload_json"]
        if hashlib.sha256(raw.encode()).hexdigest()!=item["payload_sha256"]:raise MemoryCheckpointError("Checkpoint integrity verification failed")
        item["payload"]=json.loads(raw);return item
    @requires_project("read", project_arg="pid")
    def list_checkpoints(self,pid,*,limit=50):
        self._require_project(pid)
        if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=200:raise MemoryCheckpointError("limit must be between 1 and 200")
        with self.db.connection() as c:rows=c.execute("SELECT checkpoint_id,label,created_at,payload_sha256 FROM project_checkpoints WHERE project_id=? ORDER BY created_at DESC LIMIT ?",(pid,limit)).fetchall()
        return [dict(r) for r in rows]
    # PC-P13-S003
    @requires_project("write", project_arg="pid")
    def record_session(self,pid,event_type,summary,*,session_id=None,metadata=None):
        self._require_project(pid);event=self._text(event_type,"event_type",80);summary=self._text(summary,"summary",2000)
        meta=_json(dict(metadata or {}))
        if len(meta)>8000:raise MemoryCheckpointError("Session metadata exceeds 8000 characters")
        sid=self._text(session_id,"session_id",100) if session_id else self._id("session");eid=self._id("evt")
        with self.db.transaction() as c:c.execute("INSERT INTO session_history VALUES(?,?,?,?,?,?,?)",(eid,pid,sid,event,summary,meta,self.clock()))
        return {"id":eid,"project_id":pid,"session_id":sid,"event_type":event,"summary":summary,"metadata":json.loads(meta)}
    @requires_project("read", project_arg="pid")
    def list_sessions(self,pid,*,limit=100):
        self._require_project(pid)
        if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=500:raise MemoryCheckpointError("limit must be between 1 and 500")
        with self.db.connection() as c:rows=c.execute("SELECT * FROM session_history WHERE project_id=? ORDER BY created_at DESC,id DESC LIMIT ?",(pid,limit)).fetchall()
        out=[]
        for row in rows:
            item=dict(row);item["metadata"]=json.loads(item.pop("metadata_json"));out.append(item)
        return out
    # PC-P13-S004
    @requires_project("write", project_arg="pid")
    def record_decision(self,pid,title,context,decision,rationale,*,status="accepted"): 
        self._require_project(pid)
        if status not in {"proposed","accepted","rejected","superseded"}:raise MemoryCheckpointError("Unsupported decision status")
        did=self._id("decision");now=self.clock()
        vals=(did,pid,did,self._text(title,"title",160),self._text(context,"context"),self._text(decision,"decision"),self._text(rationale,"rationale"),status,now,now)
        with self.db.transaction() as c:c.execute("INSERT INTO decision_records VALUES(?,?,?,?,?,?,?,?,?,?)",vals)
        return self.get_decision(did)
    @requires_project("read", resource_arg="did", resolver="get_decision")
    def get_decision(self,did):
        with self.db.connection() as c:row=c.execute("SELECT * FROM decision_records WHERE decision_id=?",(did,)).fetchone()
        return dict(row) if row else None
    @requires_project("read", project_arg="pid")
    def list_decisions(self,pid,*,limit=100):
        self._require_project(pid)
        if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=500:raise MemoryCheckpointError("limit must be between 1 and 500")
        with self.db.connection() as c:rows=c.execute("SELECT * FROM decision_records WHERE project_id=? ORDER BY created_at DESC LIMIT ?",(pid,limit)).fetchall()
        return [dict(r) for r in rows]
    # PC-P13-S005
    @requires_project("read", project_arg="pid")
    def generate_handoff(self,pid):
        project=self._require_project(pid);mem=self.list_memory(pid);dec=self.list_decisions(pid,limit=20)
        sessions=self.list_sessions(pid,limit=20);cps=self.list_checkpoints(pid,limit=10)
        lines=[f"# Project Handoff — {project['name']}","",f"- Project ID: {pid}",f"- Generated: {self.clock()}","","## Current project state",f"- Status: {project['status']}",f"- Tasks: {len(self.repository.list_tasks(pid))}","","## Project memory"]
        lines += [f"- **{m['memory_key']}** ({m['kind']}): {_json(m['value'])}" for m in mem] or ["- No saved memory."]
        lines += ["","## Decisions"]+[f"- **{d['title']}** — {d['decision']} (status: {d['status']}; rationale: {d['rationale']})" for d in dec] if dec else ["","## Decisions","- No recorded decisions."]
        lines += ["","## Recent sessions"]+[f"- {s['created_at']}: {s['event_type']} — {s['summary']}" for s in sessions] if sessions else ["","## Recent sessions","- No session history."]
        lines += ["","## Recovery checkpoints"]+[f"- {x['checkpoint_id']} — {x['label']} ({x['created_at']})" for x in cps] if cps else ["","## Recovery checkpoints","- No checkpoints."]
        lines += ["","## Resume instructions","- Run resume <checkpoint_id> to inspect a verified snapshot.","- Recovery is additive: existing project/task records are never overwritten."]
        return "\n".join(lines)+"\n"
    # PC-P13-S006
    def parse_resume_command(self,command):
        text=self._text(command,"command",240);parts=text.split();verb=parts[0].lower()
        if verb not in self.RESUME_VERBS or len(parts)>2:raise MemoryCheckpointError("Unsupported resume command; use help, status, handoff, checkpoint <label>, or resume <id>")
        if verb in {"status","handoff","help"} and len(parts)!=1:raise MemoryCheckpointError("This command does not accept an argument")
        if verb=="resume" and len(parts)!=2:raise MemoryCheckpointError("resume requires a checkpoint ID")
        if verb=="checkpoint" and len(parts)!=2:raise MemoryCheckpointError("checkpoint requires a label")
        return {"command":verb,"argument":parts[1] if len(parts)==2 else None}
    # PC-P13-S007
    def recover_state(self,cid,*,apply=False,project_id=None):
        if not isinstance(apply,bool):raise MemoryCheckpointError("apply must be boolean")
        cp=self.get_checkpoint(cid,project_id=project_id)
        if cp is None:raise KeyError(cid)
        payload=cp["payload"]
        if payload.get("schema_version")!=1 or not isinstance(payload.get("tasks"),list):raise MemoryCheckpointError("Unsupported checkpoint payload")
        pid=cp["project_id"]
        if self.authorization_context is not None:
            self.authorization_context.require(pid, "write" if apply else "read")
        if self.repository.get_project(pid) is None:raise MemoryCheckpointError("Original project is missing; automatic project recreation is not supported")
        existing={t["id"] for t in self.repository.list_tasks(pid)};tasks=payload["tasks"]
        if any(not isinstance(t,dict) or not all(k in t for k in ("id","title")) for t in tasks):raise MemoryCheckpointError("Checkpoint contains invalid task entries")
        missing=[t for t in tasks if t["id"] not in existing];restored=[]
        if apply:
            for t in missing:
                self.repository.create_task(t["id"],pid,t["title"],description=t.get("description",""),assignee=t.get("assignee"),priority=t.get("priority","medium"),status=t.get("status","todo"),due_at=t.get("due_at"))
                restored.append(t["id"])
            for dep in payload.get("dependencies",[]):
                if dep.get("task_id") in {t["id"] for t in tasks} and dep.get("depends_on_task_id") in {t["id"] for t in tasks}:
                    try:self.repository.add_dependency(dep["task_id"],dep["depends_on_task_id"])
                    except Exception:pass
        return {"checkpoint_id":cid,"verified":True,"apply":apply,"missing_task_ids":[t["id"] for t in missing],"restored_task_ids":restored,"skipped_existing_count":len(existing.intersection(t["id"] for t in tasks))}
    def resume(self,command,*,project_id=None):
        parsed=self.parse_resume_command(command);verb,arg=parsed["command"],parsed["argument"]
        if verb=="resume":
            cp=self.get_checkpoint(arg,project_id=project_id)
            if cp is None:raise KeyError(arg)
            return {"command":verb,"checkpoint":cp,"recovery_preview":self.recover_state(arg,apply=False,project_id=project_id)}
        if verb in {"status","handoff"} and self.authorization_context is not None:
            self.authorization_context.require_admin()
        if verb=="status":return {"command":verb,"projects":len(self.repository.list_projects())}
        if verb=="handoff":return {"command":verb,"projects":[p["id"] for p in self.repository.list_projects()]}
        if verb=="checkpoint":return {"command":verb,"label":arg,"requires_project_id":True}
        return {"command":"help","commands":["status","handoff","checkpoint <label>","resume <checkpoint_id>"]}
