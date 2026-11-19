"""Initial mobile-friendly dashboard for Project Continue."""
from __future__ import annotations

import streamlit as st

from config import load_config


config = load_config()

st.set_page_config(
    page_title="Project Continue",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("🧭 Project Continue")
st.caption("A checkpoint-driven workspace for managing project progress.")

with st.sidebar:
    st.subheader("Workspace")
    st.write(f"Environment: **{config.app_env}**")
    st.write(f"GitHub: **{'Connected configuration' if config.github_token else 'Not configured'}**")

st.subheader("Foundation status")
col1, col2, col3 = st.columns(3)
col1.metric("Phase", "01")
col2.metric("Tasks tracked", "0")
col3.metric("Verified tasks", "0")

st.info(
    "The foundation is being assembled. Project/task storage, GitHub inspection, "
    "and evidence-based verification will be added in later phases."
)

st.subheader("Safety rules")
st.markdown(
    "- A commit alone does not mark a task complete.\n"
    "- Sensitive or destructive actions require human approval.\n"
    "- Credentials belong in local environment variables, never in source files."
)

st.caption("Project Continue • Foundation preview")
