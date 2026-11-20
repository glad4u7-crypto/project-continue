"""Streamlit project and task dashboard."""
from __future__ import annotations
from database import Database,ProjectRepository
from services import ProjectManagementService,TaskManagementService
from config import get_settings
import streamlit as st

@st.cache_resource(show_spinner=False)
def _services(path:str):
 db=Database(path);repo=ProjectRepository(db);repo.initialize()
 return ProjectManagementService(repo),TaskManagementService(repo)

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

def render_project_management():
 path=get_settings().database_path;projects,tasks=_services(path)
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
