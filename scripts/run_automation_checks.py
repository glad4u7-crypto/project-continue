"""Invoke scheduled checks from a persistent host scheduler."""
from config import get_settings
from database import Database,ProjectRepository
from services.automation_engine import AutomationEngine
def main():
 db=Database(get_settings().database_path)
 try:
  repo=ProjectRepository(db); repo.initialize()
  result=AutomationEngine(repo).run_due_checks()
  print("AUTOMATION_CHECKS",result)
  return 1 if result["failed"] else 0
 finally: db.close()
if __name__=="__main__": raise SystemExit(main())
