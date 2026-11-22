"""Streamlit project and task dashboard."""
from __future__ import annotations
from database import Database,ProjectRepository
from services import ProjectManagementService,TaskManagementService
from config import get_settings
from services.authorization_context import AuthorizationContext
from services.access_control import AccessDenied
import streamlit as st
import sqlite3

def _services(path:str, authorization_context:AuthorizationContext|None=None):
 db=Database(path);repo=ProjectRepository(db);repo.initialize()
 return ProjectManagementService(repo,authorization_context),TaskManagementService(repo,authorization_context)

def _render_create(service):
 with st.expander("＋ Register a project",expanded=False):
  with st.form("create_project_form",clear_on_submit=True):
   name=st.text_input("Project name",max_chars=100);desc=st.text_area("Description",max_chars=2000)
   submit=st.form_submit_button("Create project",type="primary",use_container_width=True)
  if submit:
   try:p=service.create_project(name,desc)
   except (ValueError,KeyError) as e:st.error(str(e))
   except Exception:st.error("Project could not be created. Check the database connection.")
   else:st.success(f'Project “{p["name"]}” created.');st.rerun()

def _render_tasks(pid,service):
 st.markdown("### Task management")
 with st.expander("＋ Create task",expanded=False):
  with st.form(f"create_task_{pid}",clear_on_submit=True):
   title=st.text_input("Task title",max_chars=200);desc=st.text_area("Description",max_chars=4000)
   assignee=st.text_input("Assignee (name or email)",max_chars=120,help="Free-text label only; no user account is created.")
   a,b=st.columns(2);priority=a.selectbox("Priority",["low","medium","high","critical"],index=1);due=b.text_input("Due date (YYYY-MM-DD)")
   submit=st.form_submit_button("Create task",type="primary",use_container_width=True)
  if submit:
   try:service.create_task(pid,title,description=desc,assignee=assignee,priority=priority,due_at=due)
   except (ValueError,KeyError) as e:st.error(str(e))
   else:st.success("Task created.");st.rerun()
 a,b,c=st.columns([2,1,1]);query=a.text_input("Search tasks",key=f"task_query_{pid}")
 status=b.selectbox("Status",["all","todo","in_progress","blocked","done"],key=f"task_status_{pid}")
 priority=b.selectbox("Priority",["all","low","medium","high","critical"],key=f"task_priority_{pid}")
 for t in service.list_tasks(pid,status=status,priority=priority,query=query):
  with st.container(border=True):
   x,y,z=st.columns([3,1,1]);x.markdown(f'**{t["title"]}**');x.caption(f'Assignee: {t["assignee"] or "Unassigned"} · Due: {t["due_at"] or "—"}')
   y.metric("Priority",t["priority"].title());z.metric("Status",t["status"].replace("_"," ").title())
   if t["description"]:st.write(t["description"])
   if t["dependencies"]:st.caption("Depends on: "+", ".join(f'{d["title"]} ({d["status"]})' for d in t["dependencies"]))
   with st.expander("Edit task"):
    with st.form(f'edit_{t["id"]}'):
     title=st.text_input("Title",value=t["title"],max_chars=200);desc=st.text_area("Description",value=t["description"],max_chars=4000)
     owner=st.text_input("Assignee",value=t["assignee"] or "",max_chars=120)
     a,b,c=st.columns(3);p=a.selectbox("Priority",["low","medium","high","critical"],index=["low","medium","high","critical"].index(t["priority"]))
     s=b.selectbox("Status",["todo","in_progress","blocked","done"],index=["todo","in_progress","blocked","done"].index(t["status"]))
     due=c.text_input("Due date",value=t["due_at"] or "");save=st.form_submit_button("Save task changes")
    if save:
     try:service.update_task(t["id"],title=title,description=desc,assignee=owner,priority=p,status=s,due_at=due)
     except (ValueError,KeyError) as e:st.error(str(e))
     else:st.success("Task updated.");st.rerun()
   candidates=[q for q in service.list_tasks(pid) if q["id"]!=t["id"] and q["id"] not in t["dependency_ids"]]
   with st.expander("Dependencies"):
    for d in t["dependencies"]:
     left,right=st.columns([4,1]);left.write(f'{d["title"]} — {d["status"]}')
     if right.button("Remove",key=f'remove_{t["id"]}_{d["id"]}'):service.remove_dependency(t["id"],d["id"]);st.rerun()
    if candidates:
     opts={f'{q["title"]} [{q["id"]}]':q["id"] for q in candidates}
     with st.form(f'add_dep_{t["id"]}'):
      chosen=st.selectbox("This task depends on",list(opts));add=st.form_submit_button("Add dependency")
     if add:
      try:service.add_dependency(t["id"],opts[chosen])
      except (ValueError,KeyError) as e:st.error(str(e))
      else:st.success("Dependency added.");st.rerun()
   if t["status"]!="done":
    if t["can_complete"]:
     if st.button("Mark complete",key=f'complete_{t["id"]}'):
      try:service.complete_task(t["id"])
      except (ValueError,KeyError) as e:st.error(str(e))
      else:st.success("Task completed.");st.rerun()
    else:st.warning("Completion blocked: "+", ".join(d["title"] for d in t["pending_dependencies"]))

def _render_details(projects,tasks,pid):
 p=projects.get_project_details(pid)
 if p is None:st.warning("This project no longer exists.");return
 st.subheader(p["name"]);st.caption(p["description"] or "No description provided.")
 auth=projects.authorization_context
 if auth is not None:
  try:
   auth.require(pid,"manage"); can_manage=True
  except AccessDenied:
   can_manage=False
  if can_manage:
   access=auth.policy.access_control; db=projects.repository.database
   with st.expander("Project access and members"):
    with db.connection() as connection:
     owner_count=connection.execute("SELECT COUNT(*) AS n FROM pc_project_memberships WHERE project_id=? AND role='owner'",(pid,)).fetchone()["n"]
     users=[dict(r) for r in connection.execute("SELECT id,email,role,enabled FROM pc_users ORDER BY email")]
     members=[dict(r) for r in connection.execute("SELECT u.id,u.email,m.role FROM pc_project_memberships m JOIN pc_users u ON u.id=m.user_id WHERE m.project_id=? ORDER BY m.role,u.email",(pid,))]
    if owner_count==0 and auth.principal.get("role")=="admin":
     if st.button("Bootstrap my account as first project owner",key="bootstrap_owner_"+pid):
      try: access.bootstrap_project_owner(auth.principal,pid)
      except (AccessDenied,KeyError) as exc: st.error(str(exc))
      else: st.success("Project owner established."); st.rerun()
    if auth.principal.get("role")=="admin":
     with st.form("create_member_"+pid,clear_on_submit=True):
      new_id=st.text_input("New account ID",max_chars=100)
      new_email=st.text_input("New account email",max_chars=320)
      new_password=st.text_input("Temporary password (12+ characters)",type="password",max_chars=1024)
      new_role=st.selectbox("Account role",["owner","editor","viewer"],index=2)
      create=st.form_submit_button("Create account")
     if create:
      try: access.create_user(new_id,new_email,new_password,role=new_role)
      except (ValueError,sqlite3.IntegrityError) as exc: st.error(str(exc))
      else: st.success("Account created. Add it to this project below."); st.rerun()
    if users:
     with st.form("grant_member_"+pid):
      target=st.selectbox("Account",options=[u["id"] for u in users],format_func=lambda uid: next(f"{u['email']} · {uid}" for u in users if u["id"]==uid))
      roles=["editor","viewer"] if auth.principal.get("role")!="admin" else ["owner","editor","viewer"]
      member_role=st.selectbox("Project role",roles)
      grant=st.form_submit_button("Add or update membership")
     if grant:
      try: access.grant_project(auth.principal,pid,target,role=member_role)
      except (AccessDenied,ValueError,KeyError) as exc: st.error(str(exc))
      else: st.success("Project membership updated."); st.rerun()
    st.write("**Current members**")
    for member in members: st.caption(f"{member['email']} · {member['role']}")
 cols=st.columns(4);cols[0].metric("Progress",f'{p["progress_percent"]:.1f}%');cols[1].metric("Tasks",p["total_tasks"])
 cols[2].metric("Completed",p["completed_tasks"]);cols[3].metric("Status",p["status"].title())
 st.progress(p["progress_percent"]/100 if p["total_tasks"] else 0.0)
 cols=st.columns(4)
 for c,(label,key) in zip(cols,(("To do","todo"),("In progress","in_progress"),("Blocked","blocked"),("Done","done"))):c.metric(label,p["task_status_counts"][key])
 _render_tasks(pid,tasks)
 with st.expander("Edit project details"):
  with st.form(f"edit_project_{pid}"):
   name=st.text_input("Name",value=p["name"],max_chars=100);desc=st.text_area("Description",value=p["description"],max_chars=2000);save=st.form_submit_button("Save changes")
  if save:
   try:projects.update_project(pid,name=name,description=desc)
   except (ValueError,KeyError) as e:st.error(str(e))
   else:st.success("Project updated.");st.rerun()
 if p["status"]=="active":
  if st.button("Archive project",key=f"archive_{pid}"):projects.archive_project(pid);st.rerun()
 elif st.button("Restore project",key=f"restore_{pid}"):projects.restore_project(pid);st.rerun()
 st.markdown("#### Recent activity")
 for e in p["activity"][:10]:st.caption(f'{e["created_at"]} · {e["event_type"].replace("."," ").title()}')

def render_project_management(authorization_context:AuthorizationContext|None=None):
 path=get_settings().database_path;projects,tasks=_services(path,authorization_context)
 st.title("🧭 Project Continue");st.caption("Project workspace · task planning · progress · activity");_render_create(projects)
 a,b=st.columns([2,1]);query=a.text_input("Search projects");status=b.selectbox("Project status",["active","all","archived"],index=0)
 items=projects.list_projects(status=status,query=query);st.markdown("### Project registry")
 if not items:st.info("No matching projects. Register your first project above.");return
 for p in items:
  with st.container(border=True):
   a,b,c=st.columns([3,1,1]);a.markdown(f'**{p["name"]}**');a.caption(p["description"] or "No description")
   b.metric("Progress",f'{p["progress_percent"]:.0f}%');c.metric("Tasks",p["total_tasks"])
   st.progress(p["progress_percent"]/100 if p["total_tasks"] else 0.0)
   if st.button("Open details",key=f'open_{p["id"]}',use_container_width=True):st.session_state["selected_project_id"]=p["id"]
 selected=st.session_state.get("selected_project_id")
 if selected and any(p["id"]==selected for p in items):st.divider();_render_details(projects,tasks,selected)
 elif selected:st.session_state.pop("selected_project_id",None)
