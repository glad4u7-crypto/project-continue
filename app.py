"""Streamlit entry point for Project Continue."""
import streamlit as st
from ui.authentication import render_production_authentication
from config import settings
from ui.github_integration import render_github_integration
from ui.project_management import render_project_management
from ui.ai_brain import render_ai_brain
from ui.automation import render_automation
from ui.memory_checkpoint import render_memory_checkpoint

st.set_page_config(page_title=settings.app_name, page_icon="🧭", layout="wide")

# Development/Colab behavior is unchanged. Production fails closed behind login.
if settings.app_env == "production" and not render_production_authentication():
    st.stop()
render_project_management()
render_ai_brain()
render_automation()
render_memory_checkpoint()
render_github_integration()
st.divider()
st.caption(f"Environment: {settings.app_env} · Log level: {settings.log_level}")
