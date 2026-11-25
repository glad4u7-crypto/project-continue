"""Read-only self-check panel for Project Continue."""
from __future__ import annotations

import json

import streamlit as st

from services.self_check import run_self_check


def render_self_check(repository, settings) -> None:
    """Render diagnostics and an exportable, sanitized JSON evidence report."""
    with st.expander("🔎 Automated self-check", expanded=False):
        st.caption(
            "Runs read-only database and configuration checks. "
            "It does not create projects/tasks or modify stored data."
        )
        if st.button("Run self-check", key="run_project_continue_self_check"):
            st.session_state["project_continue_self_check_report"] = run_self_check(
                repository, settings
            )

        report = st.session_state.get("project_continue_self_check_report")
        if not report:
            st.info("Run the self-check to generate a diagnostic report.")
            return

        summary = report["summary"]
        st.metric("Overall result", report["overall"])
        a, b, c, d = st.columns(4)
        a.metric("Passed", summary["passed"])
        b.metric("Failed", summary["failed"])
        c.metric("Warnings", summary["warnings"])
        d.metric("Skipped", summary["skipped"])

        for item in report["checks"]:
            status = item["status"]
            message = f'**{item["check"]}** — {status}: {item["detail"]}'
            if status == "FAIL":
                st.error(message)
            elif status == "WARN":
                st.warning(message)
            elif status == "SKIP":
                st.info(message)
            else:
                st.success(message)

        payload = json.dumps(report, ensure_ascii=False, indent=2)
        st.download_button(
            "Download diagnostic report (JSON)",
            data=payload,
            file_name="project-continue-self-check.json",
            mime="application/json",
            key="download_project_continue_self_check",
        )
