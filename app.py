"""Streamlit entry point for Project Continue."""
import os
import streamlit as st
from ui.authentication import render_production_authentication, render_project_authentication, current_authorization_context
from config import settings
from database.runtime import get_project_repository
from ui.github_integration import render_github_integration
from ui.project_management import render_project_management
from ui.ai_brain import render_ai_brain
from ui.automation import render_automation
from ui.memory_checkpoint import render_memory_checkpoint

st.set_page_config(page_title=settings.app_name, page_icon="🧭", layout="wide")

# Initialize the shared database/repository once per configured path. All UI
# modules and authentication borrow this cached resource on every rerun.
get_project_repository(settings.database_path)

# Development/Colab behavior is unchanged. Production fails closed behind login.
membership_enforced = os.environ.get("AUTHORIZATION_ENFORCED", "").strip().lower() in {"1", "true", "yes"}
if settings.app_env == "production":
    if membership_enforced:
        if not render_project_authentication():
            st.stop()
    elif not render_production_authentication():
        st.stop()
elif membership_enforced and not render_project_authentication():
    st.stop()

authorization_context = current_authorization_context() if (settings.app_env == "production" or membership_enforced) else None
render_project_management(authorization_context)
render_ai_brain(authorization_context)
render_automation(authorization_context)
render_memory_checkpoint(authorization_context)
if authorization_context is None or authorization_context.principal.get("role") == "admin":
    render_github_integration()
else:
    st.info("GitHub integration is restricted to administrators.")
st.divider()
st.caption(f"Environment: {settings.app_env} · Log level: {settings.log_level}")
