"""Human-in-the-loop AI advisory panel."""
from __future__ import annotations

import streamlit as st

from config import get_settings
from database import Database, ProjectRepository
from services.ai_brain import AISettings, AIBrain, MockAIProvider, OpenAICompatibleProvider
from services.intelligent_task_engine import IntelligentTaskEngine
from services.authorization_context import AuthorizationContext
from services.access_control import AccessDenied


def render_ai_brain(authorization_context: AuthorizationContext | None = None) -> None:
    st.divider()
    st.header("🧠 AI Brain")
    st.caption("Read-only suggestions. AI cannot modify tasks; every suggestion requires your decision.")
    settings = get_settings()
    db = Database(settings.database_path)
    repository = ProjectRepository(db)
    repository.initialize()
    projects = [p for p in repository.list_projects() if p.get("status") == "active"]
    if authorization_context is not None:
        visible = []
        for project in projects:
            try:
                authorization_context.require(project["id"], "read")
                visible.append(project)
            except AccessDenied:
                continue
        projects = visible
    if not projects:
        st.info("Create an active project to use AI Brain.")
        return
    labels = {f"{p['name']} · {p['id']}": p['id'] for p in projects}
    selected = st.selectbox("Project context", list(labels), key="ai_brain_project")
    project_id = labels[selected]
    ai_settings = AISettings.from_env()
    if not ai_settings.enabled:
        provider = MockAIProvider()
        st.info("AI is disabled. Mock mode is active; no external provider is called.")
    elif ai_settings.provider == "openai_compatible":
        try:
            provider = OpenAICompatibleProvider(ai_settings)
        except Exception as exc:
            st.error(str(exc))
            return
    else:
        provider = MockAIProvider()
    brain_key = "ai_brain_instance"
    # Keep the one-time approval register stable across Streamlit reruns.
    if brain_key not in st.session_state or st.session_state.get("ai_brain_project_id") != project_id:
        st.session_state[brain_key] = AIBrain(
            repository, IntelligentTaskEngine(repository), provider,
            ai_settings.max_context_chars, authorization_context=authorization_context,
        )
        st.session_state["ai_brain_project_id"] = project_id
    brain = st.session_state[brain_key]
    if st.button("Generate next-step suggestion", type="primary", key="ai_brain_suggest"):
        try:
            st.session_state["ai_brain_last_result"] = brain.suggest(project_id)
        except Exception:
            st.error("AI suggestion could not be generated. Check AI configuration and provider availability.")
    result = st.session_state.get("ai_brain_last_result")
    if not result:
        return
    advice = result["ai_advice"]
    st.subheader(advice["summary"])
    st.write("**Suggested action:**", advice["suggested_action"])
    st.write("**Reason:**", advice["reason"])
    st.caption(f'Confidence reported by provider: {advice["confidence"]:.0%} · Approval: {result["approval_status"]}')
    st.warning("Approval records your decision only. It does not execute or apply the suggestion.")
    left, right = st.columns(2)
    request_id = result["approval_request_id"]
    can_decide = authorization_context is None or authorization_context.principal.get("role") in {"admin", "owner", "editor"}
    if result["approval_status"] == "pending" and can_decide:
        if left.button("Approve suggestion", key="ai_brain_approve"):
            updated = brain.approvals.decide(request_id, approved=True)
            result["approval_status"] = updated.status
            st.session_state["ai_brain_last_result"] = result
            st.rerun()
        if right.button("Reject suggestion", key="ai_brain_reject"):
            updated = brain.approvals.decide(request_id, approved=False)
            result["approval_status"] = updated.status
            st.session_state["ai_brain_last_result"] = result
            st.rerun()
    else:
        st.success(f'Decision recorded: {result["approval_status"]}. No project data was changed.')
