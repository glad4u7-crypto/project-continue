"""Automation schedule and notification panel."""
import streamlit as st
from config import get_settings
from database.runtime import get_project_repository
from services.automation_engine import AutomationEngine
from services.authorization_context import AuthorizationContext
def render_automation(authorization_context:AuthorizationContext|None=None):
 st.divider(); st.header("⚙️ Automation Engine")
 st.caption("A persistent host scheduler or manual invocation runs jobs; notifications are stored in SQLite.")
 repo=get_project_repository(get_settings().database_path)

e=AutomationEngine(repo,authorization_context=authorization_context)
 is_admin=authorization_context is None or authorization_context.principal.get("role")=="admin"
 if is_admin:
  with st.expander("Create scheduled check"):
   name=st.text_input("Schedule name","Daily database health")
   check=st.selectbox("Check",["database_health","overdue_tasks","stale_tasks"])
   interval=st.number_input("Interval seconds",min_value=60,max_value=2592000,value=86400,step=60)
   if st.button("Save schedule",key="automation_save"):
    try: e.create_schedule(name,check,interval_seconds=int(interval)); st.success("Schedule saved."); st.rerun()
    except ValueError as exc: st.error(str(exc))
  for s in e.list_schedules():
   a,b,c=st.columns([3,2,1]); a.write(s["name"]); b.caption(s["check_name"])
   if c.button("Pause" if s["enabled"] else "Enable",key="schedule_"+s["id"]): e.set_schedule_enabled(s["id"],not bool(s["enabled"])); st.rerun()
  if st.button("Run due checks now",key="automation_run"): st.write(e.run_due_checks())
 else:
  st.caption("Global scheduler controls are administrator-only.")
 st.subheader("Notifications")
 for n in e.list_notifications(limit=50):
  a,b=st.columns([5,1]); a.write(f"**{n['title']}** — {n['message']}")
  if not n["read_at"] and b.button("Mark read",key="read_"+n["id"]): e.mark_notification_read(n["id"]); st.rerun()
