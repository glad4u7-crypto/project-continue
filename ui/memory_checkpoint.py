"""Streamlit interface for durable project memory and safe recovery."""
from __future__ import annotations
import streamlit as st
from config import get_settings
from database import Database, ProjectRepository
from services.memory_checkpoint_engine import MemoryCheckpointEngine, MemoryCheckpointError


def render_memory_checkpoint() -> None:
    st.divider()
    st.header("🧠 Memory & Checkpoint Engine")
    st.caption("Save project context, record decisions, create verified checkpoints and resume safely.")
    db = Database(get_settings().database_path)
    try:
        repo = ProjectRepository(db)
        repo.initialize()
        engine = MemoryCheckpointEngine(repo)
        projects = repo.list_projects()
        if not projects:
            st.info("Create a project before saving memory or checkpoints.")
            return
        labels = {f"{p['name']} · {p['id']}": p["id"] for p in projects}
        selected = st.selectbox("Project", list(labels), key="memory_project")
        pid = labels[selected]

        with st.expander("Project memory", expanded=True):
            with st.form("memory_save_form", clear_on_submit=True):
                key = st.text_input("Memory key", max_chars=120)
                kind = st.selectbox("Memory type", sorted(engine.MEMORY_KINDS))
                value = st.text_area("Memory value (plain text or JSON)", max_chars=12000)
                save_memory = st.form_submit_button("Save memory")
            if save_memory:
                try:
                    import json
                    try:
                        parsed = json.loads(value)
                    except (ValueError, TypeError):
                        parsed = value
                    engine.remember(pid, key, parsed, kind=kind)
                    st.success("Memory saved.")
                    st.rerun()
                except (ValueError, KeyError) as exc:
                    st.error(str(exc))
            for item in engine.list_memory(pid):
                a, b = st.columns([5, 1])
                a.write(f"**{item['memory_key']}** · {item['kind']}: {item['value']}")
                if b.button("Forget", key="forget_" + item["id"]):
                    engine.forget_memory(pid, item["memory_key"])
                    st.rerun()

        with st.expander("Checkpoint storage", expanded=True):
            label = st.text_input("Checkpoint label", key="memory_checkpoint_label")
            if st.button("Create verified checkpoint", key="memory_create_checkpoint"):
                try:
                    cp = engine.create_checkpoint(pid, label)
                    st.success(f"Checkpoint saved: {cp['checkpoint_id']}")
                    st.rerun()
                except (ValueError, KeyError) as exc:
                    st.error(str(exc))
            checkpoints = engine.list_checkpoints(pid)
            if checkpoints:
                chosen = st.selectbox("Saved checkpoint", [x["checkpoint_id"] for x in checkpoints],
                                      format_func=lambda x: next(f"{c['label']} · {x}" for c in checkpoints if c["checkpoint_id"] == x),
                                      key="memory_checkpoint_select")
                cp = engine.get_checkpoint(chosen, project_id=pid)
                st.caption(f"SHA-256: {cp['payload_sha256']}")
                if st.button("Preview recovery", key="memory_recovery_preview"):
                    st.session_state["memory_recovery_target"] = chosen
                target = st.session_state.get("memory_recovery_target")
                if target == chosen:
                    preview = engine.recover_state(chosen, apply=False, project_id=pid)
                    st.write({"verified": preview["verified"], "missing_task_ids": preview["missing_task_ids"],
                              "existing_tasks_skipped": preview["skipped_existing_count"]})
                    st.warning("Applying recovery adds missing tasks only. Existing tasks and project details are not overwritten.")
                    if preview["missing_task_ids"] and st.checkbox("I understand: restore missing tasks from this checkpoint", key="memory_recovery_confirm"):
                        if st.button("Apply additive recovery", type="primary", key="memory_recovery_apply"):
                            result = engine.recover_state(chosen, apply=True, project_id=pid)
                            st.success(f"Restored {len(result['restored_task_ids'])} task(s).")
                            st.session_state.pop("memory_recovery_target", None)
                            st.rerun()
                    elif not preview["missing_task_ids"]:
                        st.info("No missing tasks. Recovery would make no changes.")

        with st.expander("Session history and decisions"):
            with st.form("memory_session_form", clear_on_submit=True):
                event_type = st.text_input("Session event", value="progress", max_chars=80)
                summary = st.text_area("Session summary", max_chars=2000)
                add_session = st.form_submit_button("Record session")
            if add_session:
                try:
                    engine.record_session(pid, event_type, summary)
                    st.success("Session recorded.")
                    st.rerun()
                except (ValueError, KeyError) as exc:
                    st.error(str(exc))
            with st.form("memory_decision_form", clear_on_submit=True):
                title = st.text_input("Decision title", max_chars=160)
                context = st.text_area("Context")
                decision = st.text_area("Decision")
                rationale = st.text_area("Rationale")
                add_decision = st.form_submit_button("Record decision")
            if add_decision:
                try:
                    engine.record_decision(pid, title, context, decision, rationale)
                    st.success("Decision recorded.")
                    st.rerun()
                except (ValueError, KeyError) as exc:
                    st.error(str(exc))
            st.write("**Recent sessions**")
            for item in engine.list_sessions(pid, limit=10):
                st.caption(f"{item['created_at']} · {item['event_type']}: {item['summary']}")
            st.write("**Decision records**")
            for item in engine.list_decisions(pid, limit=10):
                st.write(f"- **{item['title']}** — {item['decision']} ({item['status']})")

        with st.expander("Handoff and resume"):
            handoff = engine.generate_handoff(pid)
            st.download_button("Download project handoff", handoff,
                               file_name=f"project-handoff-{pid}.md", mime="text/markdown")
            command = st.text_input("Resume command", placeholder="resume <checkpoint_id>",
                                    key="memory_resume_command")
            if st.button("Parse resume command", key="memory_parse_resume"):
                try:
                    result = engine.resume(command, project_id=pid)
                    st.session_state["memory_resume_result"] = result
                except (ValueError, KeyError) as exc:
                    st.error(str(exc))
            result = st.session_state.get("memory_resume_result")
            if result:
                st.json({k: v for k, v in result.items() if k != "checkpoint"})
                if result.get("checkpoint"):
                    st.write("Checkpoint verified; recovery preview is available above.")
    except MemoryCheckpointError as exc:
        st.error(str(exc))
    finally:
        db.close()
