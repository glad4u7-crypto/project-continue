"""Fail-closed production login gate for the Streamlit operator dashboard."""
from __future__ import annotations

import os
import uuid

import streamlit as st

from config import settings
from database.runtime import get_project_repository
from services.access_control import AccessControl
from services.authorization import ProjectAuthorization
from services.authorization_context import AuthorizationContext


@st.cache_resource(show_spinner=False)
def _access_control():
    key = os.environ.get("SESSION_SIGNING_KEY", "")
    repository = get_project_repository(settings.database_path)
    db = repository.database
    if settings.database_backend == "postgresql":
        from services.postgres_access_control import PostgresAccessControl
        access = PostgresAccessControl(db, key)
    else:
        access = AccessControl(db, key)
    with db.connection() as connection:
        count = connection.execute("SELECT COUNT(*) AS n FROM pc_users").fetchone()["n"]
    if count == 0:
        email = os.environ.get("INITIAL_ADMIN_EMAIL", "").strip()
        password = os.environ.get("INITIAL_ADMIN_PASSWORD", "")
        if email and password:
            access.create_user("admin-" + uuid.uuid4().hex, email, password, role="admin")
    return access


def render_production_authentication() -> bool:
    """Return true only for a verified administrator; never trust UI visibility alone."""
    try:
        access = _access_control()
    except Exception:
        st.error("Production authentication is not configured. Contact the operator.")
        return False

    token = st.session_state.get("_pc_operator_session")
    principal = access.verify_session(token) if isinstance(token, str) else None
    if principal is not None and principal["role"] == "admin":
        st.sidebar.caption("Authenticated production operator")
        if st.sidebar.button("Sign out", key="pc_production_signout"):
            st.session_state.pop("_pc_operator_session", None)
            st.rerun()
        return True

    st.title("Project Continue — Sign in")
    st.info("Production access requires an authorized operator account.")
    with st.form("pc_production_login", clear_on_submit=True):
        email = st.text_input("Email", max_chars=320)
        password = st.text_input("Password", type="password", max_chars=1024)
        submitted = st.form_submit_button("Sign in", type="primary")
    if submitted:
        principal = access.authenticate(email, password)
        if principal is None or principal["role"] != "admin":
            st.error("Sign-in failed or account is not authorized.")
        else:
            st.session_state["_pc_operator_session"] = access.issue_session(principal)
            st.rerun()
    return False


def current_authorization_context() -> AuthorizationContext | None:
    """Return request-scoped authorization only for a currently verified signed session."""
    try:
        access = _access_control()
        token = st.session_state.get("_pc_operator_session")
        principal = access.verify_session(token) if isinstance(token, str) else None
        return AuthorizationContext(ProjectAuthorization(access), principal) if principal else None
    except Exception:
        return None


def render_project_authentication() -> bool:
    """Authenticate any enabled account when membership-based access is explicitly enabled."""
    try:
        access = _access_control()
    except Exception:
        st.error("Project authorization is not configured. Contact the operator.")
        return False
    token = st.session_state.get("_pc_operator_session")
    principal = access.verify_session(token) if isinstance(token, str) else None
    if principal is not None:
        st.sidebar.caption("Authenticated project member · " + principal["role"])
        if st.sidebar.button("Sign out", key="pc_member_signout"):
            st.session_state.pop("_pc_operator_session", None)
            st.rerun()
        return True
    st.title("Project Continue — Sign in")
    st.info("Sign in with an enabled account. Project data is limited by membership and role.")
    with st.form("pc_member_login", clear_on_submit=True):
        email = st.text_input("Email", max_chars=320)
        password = st.text_input("Password", type="password", max_chars=1024)
        submitted = st.form_submit_button("Sign in", type="primary")
    if submitted:
        principal = access.authenticate(email, password)
        if principal is None:
            st.error("Sign-in failed or account is not authorized.")
        else:
            st.session_state["_pc_operator_session"] = access.issue_session(principal)
            st.rerun()
    return False
