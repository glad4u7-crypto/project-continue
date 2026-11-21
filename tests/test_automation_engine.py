"""Phase 12 isolated SQLite automation tests."""
from datetime import datetime,timezone
import pytest
from database import Database,ProjectRepository
from services.automation_engine import AutomationEngine
from services.project_management import ProjectManagementService
from services.task_management import TaskManagementService

@pytest.fixture
def ws(tmp_path):
 db=Database(tmp_path/"automation.db"); repo=ProjectRepository(db); repo.initialize()
 p=ProjectManagementService(repo).create_project("Automation")
 yield db,repo,p["id"]
 db.close()

def test_status_rule_and_deduplicated_notification(ws):
 _,repo,pid=ws; e=AutomationEngine(repo); tasks=TaskManagementService(repo)
 e.create_task_status_rule(pid,"done"); t=tasks.create_task(pid,"Ship"); old=repo.get_task(t["id"])
 tasks.set_status(t["id"],"done")
 assert len(e.list_notifications(unread_only=True))==1
 assert e.handle_task_update(old,repo.get_task(t["id"]))==0

def test_validation_and_allowlist(ws):
 _,repo,pid=ws; e=AutomationEngine(repo)
 with pytest.raises(ValueError): e.create_task_status_rule(pid,"bad")
 with pytest.raises(ValueError): e.create_schedule("Bad","arbitrary")
 with pytest.raises(ValueError): e.create_schedule("Bad","database_health",interval_seconds=1)
 with pytest.raises(ValueError): e.create_schedule("Bad","database_health",max_attempts=9)

def test_due_check_runs_once_and_reschedules(ws):
 _,repo,_=ws; now=datetime(2026,1,1,tzinfo=timezone.utc); e=AutomationEngine(repo,clock=lambda:now)
 e.create_schedule("Health","database_health",interval_seconds=60)
 assert e.run_due_checks()["succeeded"]==1
 assert e.run_due_checks()["claimed"]==0

def test_overdue_check_creates_notification(ws):
 _,repo,pid=ws; now=datetime(2026,1,10,tzinfo=timezone.utc)
 TaskManagementService(repo).create_task(pid,"Late",due_at="2026-01-01T00:00:00+00:00")
 e=AutomationEngine(repo,clock=lambda:now)
 assert e._run_check("overdue_tasks")["overdue_count"]==1
 assert e.list_notifications()[0]["kind"]=="overdue_task"

def test_failure_backoff_and_manual_retry(ws,monkeypatch):
 _,repo,_=ws; now=datetime(2026,1,1,tzinfo=timezone.utc); e=AutomationEngine(repo,clock=lambda:now)
 sid=e.create_schedule("Health","database_health",max_attempts=1)
 monkeypatch.setattr(e,"_run_check",lambda _: (_ for _ in ()).throw(RuntimeError("private detail")))
 assert e.run_due_checks()["failed"]==1 and e.list_schedules()[0]["enabled"]==0
 assert "private detail" not in e.list_notifications()[0]["message"]
 assert e.retry_failed(sid)

def test_notification_read_and_schedule_pause(ws):
 _,repo,pid=ws; e=AutomationEngine(repo); sid=e.create_schedule("Health","database_health")
 assert e.set_schedule_enabled(sid,False) and e.run_due_checks()["claimed"]==0
 e.notify(pid,"system","Notice","Message"); n=e.list_notifications()[0]
 assert e.mark_notification_read(n["id"]) and not e.mark_notification_read(n["id"])
 assert e.list_notifications(unread_only=True)==[]
