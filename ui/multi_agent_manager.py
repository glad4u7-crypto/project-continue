"""Streamlit interface for project-scoped multi-agent coordination."""
import streamlit as st

from config import get_settings
from database.runtime import get_project_repository
from services.multi_agent_manager import AgentManagerError, MultiAgentManager
from services.project_management import ProjectManagementService
from services.authorization_context import AuthorizationContext
from services.access_control import AccessDenied


def render_multi_agent_manager(authorization_context: AuthorizationContext | None = None):
    st.divider()
    st.header("🤖 Multi-Agent Manager")
    st.caption("Register project agents, assign roles, select capable agents and exchange scoped messages.")
    repository = get_project_repository(get_settings().database_path)
    projects = ProjectManagementService(repository, authorization_context).list_projects()
    if not projects:
        st.info("Create or join a project before managing agents.")
        return
    labels = {f"{item['name']} · {item['id']}": item["id"] for item in projects}
    selected_label = st.selectbox("Agent workspace", list(labels), key="multi_agent_project")
    project_id = labels[selected_label]
    manager = MultiAgentManager(repository, authorization_context=authorization_context)
    agents = manager.list_agents(project_id, include_disabled=True)
    active = [agent for agent in agents if agent["status"] == "active"]

    registration, roles, selection, messages = st.tabs(
        ["U01 · Registration", "U02 · Roles", "U03 · Selection", "U04 · Communication"]
    )
    with registration:
        with st.form("multi_agent_register"):
            name = st.text_input("Agent name", max_chars=80)
            description = st.text_area("Description", max_chars=500)
            capabilities = st.text_input("Capabilities (comma-separated)", placeholder="research, summarize, code.review")
            submitted = st.form_submit_button("Register agent")
        if submitted:
            try:
                caps = [value.strip() for value in capabilities.split(",") if value.strip()]
                manager.register_agent(project_id, name, description=description, capabilities=caps)
                st.success("Agent registered.")
                st.rerun()
            except (AgentManagerError, AccessDenied, KeyError) as exc:
                st.error(str(exc))
        if agents:
            st.dataframe([{"Name": a["name"], "Status": a["status"], "Roles": ", ".join(a["roles"]),
                           "Capabilities": ", ".join(a["capabilities"]), "Selections": a["selection_count"]}
                          for a in agents], use_container_width=True, hide_index=True)
            agent_names = {f"{a['name']} · {a['id']}": a["id"] for a in agents}
            chosen = st.selectbox("Agent status control", list(agent_names), key="multi_agent_status_agent")
            status = st.selectbox("Status", ["active", "disabled"], key="multi_agent_status_value")
            if st.button("Update agent status"):
                try:
                    manager.set_agent_status(project_id, agent_names[chosen], status)
                    st.success("Agent status updated.")
                    st.rerun()
                except AccessDenied as exc:
                    st.error(str(exc))
        else:
            st.info("No agents registered in this project yet.")

    with roles:
        if not agents:
            st.info("Register an agent before assigning roles.")
        else:
            agent_names = {f"{a['name']} · {a['id']}": a["id"] for a in agents}
            chosen = st.selectbox("Agent", list(agent_names), key="multi_agent_role_agent")
            role = st.selectbox("Role", sorted(MultiAgentManager.ROLES), key="multi_agent_role")
            if st.button("Assign role"):
                try:
                    manager.assign_role(project_id, agent_names[chosen], role)
                    st.success("Role assigned.")
                    st.rerun()
                except (AgentManagerError, AccessDenied, KeyError) as exc:
                    st.error(str(exc))
            current = manager.get_agent(project_id, agent_names[chosen]) or {}
            if current.get("roles"):
                remove = st.selectbox("Assigned role to remove", current["roles"], key="multi_agent_remove_role")
                if st.button("Remove role"):
                    try:
                        manager.remove_role(project_id, agent_names[chosen], remove)
                        st.success("Role removed.")
                        st.rerun()
                    except AccessDenied as exc:
                        st.error(str(exc))
            st.caption("Available roles: " + ", ".join(sorted(MultiAgentManager.ROLES)))

    with selection:
        role = st.selectbox("Required role", sorted(MultiAgentManager.ROLES), key="multi_agent_select_role")
        required = st.text_input("Required capabilities (comma-separated)", key="multi_agent_required_caps")
        if st.button("Select best matching agent"):
            try:
                chosen = manager.select_agent(
                    project_id, role,
                    required_capabilities=[v.strip() for v in required.split(",") if v.strip()],
                )
                if chosen:
                    st.success(f"Selected {chosen['name']} ({chosen['id']}).")
                else:
                    st.warning("No active agent matches this role and capability set.")
            except (AgentManagerError, AccessDenied) as exc:
                st.error(str(exc))

    with messages:
        if len(active) < 2:
            st.info("At least two active agents are required for communication.")
        else:
            options = {f"{a['name']} · {a['id']}": a["id"] for a in active}
            sender_label = st.selectbox("Sender agent", list(options), key="multi_agent_sender")
            recipient_options = {label: value for label, value in options.items() if value != options[sender_label]}
            recipient_label = st.selectbox("Recipient agent", list(recipient_options), key="multi_agent_recipient")
            message_type = st.selectbox("Message type", sorted(MultiAgentManager.MESSAGE_TYPES), key="multi_agent_message_type")
            body = st.text_area("Message", max_chars=12000, key="multi_agent_message_body")
            if st.button("Send agent message"):
                try:
                    manager.send_message(project_id, options[sender_label], recipient_options[recipient_label],
                                         {"text": body}, message_type=message_type)
                    st.success("Message queued.")
                    st.rerun()
                except (AgentManagerError, AccessDenied) as exc:
                    st.error(str(exc))
            recipient_id = recipient_options[recipient_label]
            inbox = manager.list_messages(project_id, recipient_id, inbox=True, limit=50)
            st.subheader(f"Inbox · {recipient_label}")
            if not inbox:
                st.caption("No messages.")
            for item in inbox:
                st.write(f"**{item['message_type']}** · {item['created_at']} · {item['status']}")
                st.write(item["payload"].get("text", item["payload"]))
                if item["status"] == "queued" and st.button("Mark read", key="agent_message_read_" + item["id"]):
                    try:
                        manager.mark_message_read(project_id, recipient_id, item["id"])
                        st.rerun()
                    except AccessDenied as exc:
                        st.error(str(exc))
