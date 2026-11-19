"""Initial Streamlit entry point for Project Continue."""

import streamlit as st

from config import settings


st.set_page_config(
    page_title=settings.app_name,
    page_icon="🧭",
    layout="wide",
)

st.title("🧭 Project Continue")
st.caption("Your workspace for organized, verifiable project progress.")

st.info(
    "Foundation checkpoint: the application shell is ready. "
    "Project storage, task tracking, GitHub inspection, and verification "
    "will be added in subsequent phases."
)

left, right = st.columns(2)
with left:
    st.subheader("Project workspace")
    st.write("Project registration and project status are coming next.")
with right:
    st.subheader("Next task")
    st.write("Task prioritization and dependency-aware recommendations are coming next.")

st.divider()
st.caption(f"Environment: {settings.app_env} · Log level: {settings.log_level}")
