"""Streamlit entry point for Project Continue."""

import streamlit as st

from config import settings
from ui.project_management import render_project_management


st.set_page_config(
    page_title=settings.app_name,
    page_icon="🧭",
    layout="wide",
)

render_project_management()
st.divider()
st.caption(f"Environment: {settings.app_env} · Log level: {settings.log_level}")
