"""Streamlit project-management dashboard."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from database import Database, ProjectRepository
from services import ProjectManagementService


@st.cache_resource(show_spinner=False)
def _service(database_path: str) -> ProjectManagementService:
    database = Database(database_path)
    repository = ProjectRepository(database)
    repository.initialize()
    return ProjectManagementService(repository)


def _render_create(service: ProjectManagementService) -> None:
    with st.expander("＋ Register a project", expanded=False):
        with st.form("create_project_form", clear_on_submit=True):
            name = st.text_input("Project name", max_chars=100, placeholder="e.g. Website redesign")
            description = st.text_area("Description", max_chars=2000, placeholder="What is this project about?")
            submitted = st.form_submit_button("Create project", type="primary", use_container_width=True)
        if submitted:
            try:
                project = service.create_project(name, description)
            except (ValueError, KeyError) as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Project could not be created: {exc}")
            else:
                st.success(f'Project “{project["name"]}” created.')
                st.rerun()


def _render_project_details(service: ProjectManagementService, project_id: str) -> None:
    project = service.get_project_details(project_id)
    if project is None:
        st.warning("This project no longer exists.")
        return
    st.subheader(project["name"])
    st.caption(project["description"] or "No description provided.")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Progress", f'{project["progress_percent"]:.1f}%')
    metric_cols[1].metric("Tasks", project["total_tasks"])
    metric_cols[2].metric("Completed", project["completed_tasks"])
    metric_cols[3].metric("Status", project["status"].title())
    st.progress(project["progress_percent"] / 100 if project["total_tasks"] else 0.0)

    with st.expander("Edit project details"):
        with st.form(f"edit_project_{project_id}"):
            name = st.text_input("Name", value=project["name"], max_chars=100)
            description = st.text_area("Description", value=project["description"], max_chars=2000)
            save = st.form_submit_button("Save changes", use_container_width=True)
        if save:
            try:
                service.update_project(project_id, name=name, description=description)
            except (ValueError, KeyError) as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Project could not be updated: {exc}")
            else:
                st.success("Project updated.")
                st.rerun()

    if project["status"] == "active":
        if st.button("Archive project", key=f"archive_{project_id}"):
            try:
                service.archive_project(project_id)
            except Exception as exc:
                st.error(f"Project could not be archived: {exc}")
            else:
                st.success("Project archived.")
                st.rerun()
    else:
        if st.button("Restore project", key=f"restore_{project_id}"):
            try:
                service.restore_project(project_id)
            except Exception as exc:
                st.error(f"Project could not be restored: {exc}")
            else:
                st.success("Project restored.")
                st.rerun()

    st.markdown("#### Recent activity")
    if project["activity"]:
        for event in project["activity"][:10]:
            st.caption(f'{event["created_at"]} · {event["event_type"].replace(".", " ").title()}')
    else:
        st.caption("No activity recorded yet.")


def render_project_management() -> None:
    """Render the complete project registry and project details workspace."""
    default_path = Path(".data/project_continue.sqlite3")
    database_path = os.getenv("PROJECT_CONTINUE_DB", str(default_path))
    service = _service(database_path)

    st.title("🧭 Project Continue")
    st.caption("Project workspace · registration · lifecycle · progress")
    _render_create(service)

    search_col, filter_col = st.columns([2, 1])
    with search_col:
        query = st.text_input("Search projects", placeholder="Search by project name or description")
    with filter_col:
        status = st.selectbox("Project status", ["active", "all", "archived"], index=0)

    projects = service.list_projects(status=status, query=query)
    st.markdown("### Project registry")
    if not projects:
        st.info("No matching projects. Register your first project above.")
        return

    for project in projects:
        with st.container(border=True):
            top = st.columns([3, 1, 1])
            top[0].markdown(f'**{project["name"]}**')
            top[0].caption(project["description"] or "No description")
            top[1].metric("Progress", f'{project["progress_percent"]:.0f}%')
            top[2].metric("Tasks", project["total_tasks"])
            st.progress(project["progress_percent"] / 100 if project["total_tasks"] else 0.0)
            if st.button("Open details", key=f'open_{project["id"]}', use_container_width=True):
                st.session_state["selected_project_id"] = project["id"]

    selected_id = st.session_state.get("selected_project_id")
    if selected_id and any(item["id"] == selected_id for item in projects):
        st.divider()
        _render_project_details(service, selected_id)
    elif selected_id:
        st.session_state.pop("selected_project_id", None)
