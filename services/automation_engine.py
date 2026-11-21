"""SQLite-backed allow-listed automation, scheduled checks, recovery and notifications."""
from datetime import datetime,timedelta,timezone
import json,sqlite3,uuid

def _now(): return datetime.now(timezone.utc)
def _iso(v): return v.isoformat()
class AutomationEngine:
 CHECKS=frozenset({"database_health","overdue_tasks","stale_tasks"})
 def __init__(self,repository,clock=_now):
  self.repository,self.db,self.clock=repository,repository.database,clock
  with self.db.connection() as c:
   c.executescript("""
   CREATE TABLE IF NOT EXISTS automation_rules(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,event_type TEXT NOT NULL,target_status TEXT,enabled INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS automation_schedules(id TEXT PRIMARY KEY,name TEXT NOT NULL,check_name TEXT NOT NULL,interval_seconds INTEGER NOT NULL CHECK(interval_seconds BETWEEN 60 AND 2592000),next_run_at TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 1,failure_count INTEGER NOT NULL DEFAULT 0,max_attempts INTEGER NOT NULL DEFAULT 3,created_at TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS automation_runs(id TEXT PRIMARY KEY,schedule_id TEXT NOT NULL REFERENCES automation_schedules(id) ON DELETE CASCADE,started_at TEXT NOT NULL,finished_at TEXT,status TEXT NOT NULL,attempt INTEGER NOT NULL,result_json TEXT NOT NULL DEFAULT '{}',error_type TEXT);
   CREATE TABLE IF NOT EXISTS automation_notifications(id TEXT PRIMARY KEY,project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,kind TEXT NOT NULL,title TEXT NOT NULL,message TEXT NOT NULL,dedupe_key TEXT UNIQUE,created_at TEXT NOT NULL,read_at TEXT);
   CREATE INDEX IF NOT EXISTS idx_automation_due ON automation_schedules(enabled,next_run_at);
   CREATE INDEX IF NOT EXISTS idx_automation_notifications ON automation_notifications(read_at,created_at);
   """)
 @staticmethod
 def _id(p): return p+"-"+uuid.uuid4().hex[:16]
 def create_task_status_rule(self,project_id,target_status):
  if self.repository.get_project(project_id) is None: raise KeyError(project_id)
  if target_status not in {"todo","in_progress","blocked","done"}: raise ValueError("Unsupported task status")
  rid=self._id("rule")
  with self.db.transaction() as c: c.execute("INSERT INTO automation_rules VALUES(?,?,?,?,1,?)",(rid,project_id,"task.status_changed",target_status,_iso(self.clock())))
  return rid
 def handle_task_update(self,old,new):
  if old.get("status")==new.get("status"): return 0
  with self.db.connection() as c: rules=c.execute("SELECT * FROM automation_rules WHERE project_id=? AND enabled=1 AND event_type='task.status_changed'",(new["project_id"],)).fetchall()
  n=0
  for r in rules:
   if r["target_status"] in (None,new["status"]):
    key=f"rule:{r['id']}:task:{new['id']}:updated:{new['updated_at']}"
    n+=int(self.notify(new["project_id"],"task_status","Task status changed",f"{new['title']} is now {new['status'].replace('_',' ')}.",dedupe_key=key))
  return n
 def notify(self,project_id,kind,title,message,*,dedupe_key=None):
  if kind not in {"task_status","overdue_task","automation_failure","system"}: raise ValueError("Unsupported notification kind")
  if not isinstance(title,str) or not title.strip() or len(title)>160 or not isinstance(message,str) or not message.strip() or len(message)>1000: raise ValueError("Invalid notification text")
  with self.db.transaction() as c:
   try: c.execute("INSERT INTO automation_notifications VALUES(?,?,?,?,?,?,?,NULL)",(self._id("ntf"),project_id,kind,title.strip(),message.strip(),dedupe_key,_iso(self.clock())))
   except sqlite3.IntegrityError:
    if dedupe_key: return False
    raise
  return True
 def list_notifications(self,*,unread_only=False,limit=50):
  if not 1<=limit<=200: raise ValueError("limit must be between 1 and 200")
  where="WHERE read_at IS NULL" if unread_only else ""
  with self.db.connection() as c: rows=c.execute(f"SELECT * FROM automation_notifications {where} ORDER BY created_at DESC LIMIT ?",(limit,)).fetchall()
  return [dict(x) for x in rows]
 def mark_notification_read(self,nid):
  with self.db.transaction() as c: cur=c.execute("UPDATE automation_notifications SET read_at=? WHERE id=? AND read_at IS NULL",(_iso(self.clock()),nid))
  return cur.rowcount==1
 def create_schedule(self,name,check_name,*,interval_seconds=86400,max_attempts=3,first_run_at=None):
  if not isinstance(name,str) or not name.strip() or len(name)>100: raise ValueError("Schedule name must contain 1-100 characters")
  if check_name not in self.CHECKS: raise ValueError("Check is not allow-listed")
  if isinstance(interval_seconds,bool) or not isinstance(interval_seconds,int) or not 60<=interval_seconds<=2592000: raise ValueError("interval_seconds must be between 60 and 2592000")
  if isinstance(max_attempts,bool) or not isinstance(max_attempts,int) or not 1<=max_attempts<=5: raise ValueError("max_attempts must be between 1 and 5")
  sid=self._id("sch"); now=self.clock()
  with self.db.transaction() as c: c.execute("INSERT INTO automation_schedules(id,name,check_name,interval_seconds,next_run_at,max_attempts,created_at) VALUES(?,?,?,?,?,?,?)",(sid,name.strip(),check_name,interval_seconds,_iso(first_run_at or now),max_attempts,_iso(now)))
  return sid
 def list_schedules(self):
  with self.db.connection() as c: rows=c.execute("SELECT * FROM automation_schedules ORDER BY created_at").fetchall()
  return [dict(x) for x in rows]
 def set_schedule_enabled(self,sid,enabled):
  if not isinstance(enabled,bool): raise ValueError("enabled must be boolean")
  with self.db.transaction() as c: cur=c.execute("UPDATE automation_schedules SET enabled=? WHERE id=?",(int(enabled),sid))
  return cur.rowcount==1
 def _run_check(self,name):
  if name=="database_health": return {"ok":bool(self.db.health_check())}
  if name=="overdue_tasks":
   with self.db.connection() as c: rows=c.execute("SELECT id,project_id,title,due_at FROM tasks WHERE status!='done' AND due_at IS NOT NULL AND due_at<? ORDER BY due_at LIMIT 200",(_iso(self.clock()),)).fetchall()
   for r in rows: self.notify(r["project_id"],"overdue_task","Overdue task",f"{r['title']} was due {r['due_at']}.",dedupe_key=f"overdue:{r['id']}:{r['due_at']}")
   return {"ok":True,"overdue_count":len(rows)}
  if name=="stale_tasks":
   cutoff=_iso(self.clock()-timedelta(days=7))
   with self.db.connection() as c: rows=c.execute("SELECT id,project_id,title FROM tasks WHERE status IN ('todo','in_progress','blocked') AND updated_at<? ORDER BY updated_at LIMIT 200",(cutoff,)).fetchall()
   for r in rows: self.notify(r["project_id"],"system","Task needs attention",f"{r['title']} has not changed for seven days.",dedupe_key=f"stale:{r['id']}:{cutoff[:10]}")
   return {"ok":True,"stale_count":len(rows)}
  raise ValueError("Unknown scheduled check")
 def run_due_checks(self,*,limit=20):
  if not 1<=limit<=100: raise ValueError("limit must be between 1 and 100")
  now=self.clock().astimezone(timezone.utc)
  with self.db.connection() as c: due=c.execute("SELECT * FROM automation_schedules WHERE enabled=1 AND next_run_at<=? ORDER BY next_run_at LIMIT ?",(_iso(now),limit)).fetchall()
  out={"claimed":0,"succeeded":0,"failed":0,"runs":[]}
  for s in due:
   rid=self._id("run"); attempt=int(s["failure_count"])+1
   with self.db.transaction() as c:
    cur=c.execute("UPDATE automation_schedules SET next_run_at=? WHERE id=? AND enabled=1 AND next_run_at=?",(_iso(now+timedelta(seconds=s["interval_seconds"])),s["id"],s["next_run_at"]))
    if cur.rowcount!=1: continue
    c.execute("INSERT INTO automation_runs(id,schedule_id,started_at,status,attempt) VALUES(?,?,?,'running',?)",(rid,s["id"],_iso(now),attempt))
   out["claimed"]+=1
   try:
    result=self._run_check(s["check_name"])
    if not result.get("ok"): raise RuntimeError("Scheduled check failed")
    with self.db.transaction() as c:
     c.execute("UPDATE automation_runs SET finished_at=?,status='success',result_json=? WHERE id=?",(_iso(self.clock()),json.dumps(result,sort_keys=True),rid))
     c.execute("UPDATE automation_schedules SET failure_count=0 WHERE id=?",(s["id"],))
    out["succeeded"]+=1; out["runs"].append({"schedule_id":s["id"],"status":"success","result":result})
   except Exception as exc:
    failures=attempt; exhausted=failures>=int(s["max_attempts"]); delay=min(3600,60*(2**min(failures-1,6))); retry=self.clock()+timedelta(seconds=delay)
    with self.db.transaction() as c:
     c.execute("UPDATE automation_runs SET finished_at=?,status='failed',error_type=? WHERE id=?",(_iso(self.clock()),type(exc).__name__,rid))
     c.execute("UPDATE automation_schedules SET failure_count=?,enabled=?,next_run_at=? WHERE id=?",(failures,0 if exhausted else 1,_iso(retry),s["id"]))
    self.notify(None,"automation_failure","Scheduled check failed",f"{s['name']} failed ({type(exc).__name__}); "+("retries exhausted." if exhausted else f"retry in {delay} seconds."),dedupe_key=f"failure:{s['id']}:{failures}:{_iso(now)[:16]}")
    out["failed"]+=1; out["runs"].append({"schedule_id":s["id"],"status":"failed","attempt":failures,"retry_at":_iso(retry)})
  return out
 def retry_failed(self,sid):
  with self.db.transaction() as c: cur=c.execute("UPDATE automation_schedules SET enabled=1,failure_count=0,next_run_at=? WHERE id=?",(_iso(self.clock()),sid))
  return cur.rowcount==1
