"""Streamlit entry point for Project Continue."""

import streamlit as st

from config import settings
from ui.github_integration import render_github_integration
from ui.project_management import render_project_management
from ui.ai_brain import render_ai_brain


st.set_page_config(
    page_title=settings.app_name,
    page_icon="🧭",
    layout="wide",
)

render_project_management()
render_ai_brain()
render_github_integration()
st.divider()
st.caption(f"Environment: {settings.app_env} · Log level: {settings.log_level}")
