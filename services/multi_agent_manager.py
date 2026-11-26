"""Project-scoped multi-agent registry, role assignment, selection and messaging."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from services.authorization_context import AuthorizationContext


class AgentManagerError(ValueError):
    """Raised when an agent operation violates the manager contract."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MultiAgentManager:
    """Persistent multi-agent coordination backed by the configured project DB.

    All records are project-scoped and additive. No existing project/task rows
    are modified. The service works with both repository database adapters.
    """

    ROLES = frozenset({"coordinator", "planner", "researcher", "executor", "reviewer", "monitor"})
    MESSAGE_TYPES = frozenset({"task", "request", "response", "status", "handoff"})
    MAX_CAPABILITIES = 32
    MAX_PAYLOAD_BYTES = 16384

    def __init__(self, repository: Any, *, clock=_utc_now,
                 authorization_context: AuthorizationContext | None = None):
        self.repository = repository
        self.db = repository.database
        self.clock = clock
        self.authorization_context = authorization_context
        with self.db.connection() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS pc_agents (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    capabilities_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','disabled')),
                    selection_count INTEGER NOT NULL DEFAULT 0,
                    last_selected_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(project_id, name)
                );
                CREATE TABLE IF NOT EXISTS pc_agent_roles (
                    agent_id TEXT NOT NULL REFERENCES pc_agents(id) ON DELETE CASCADE,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    assigned_at TEXT NOT NULL,
                    PRIMARY KEY(agent_id, role)
                );
                CREATE INDEX IF NOT EXISTS idx_pc_agent_roles_project_role
                    ON pc_agent_roles(project_id, role);
                CREATE TABLE IF NOT EXISTS pc_agent_selections (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    agent_id TEXT NOT NULL REFERENCES pc_agents(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    selected_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_pc_agent_selection_project
                    ON pc_agent_selections(project_id, selected_at);
                CREATE TABLE IF NOT EXISTS pc_agent_messages (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    sender_agent_id TEXT NOT NULL REFERENCES pc_agents(id) ON DELETE CASCADE,
                    recipient_agent_id TEXT NOT NULL REFERENCES pc_agents(id) ON DELETE CASCADE,
                    message_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','read')),
                    created_at TEXT NOT NULL,
                    read_at TEXT,
                    CHECK(sender_agent_id <> recipient_agent_id)
                );
                CREATE INDEX IF NOT EXISTS idx_pc_agent_messages_inbox
                    ON pc_agent_messages(project_id, recipient_agent_id, status, created_at);
            """)

    @staticmethod
    def _id(prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex}"

    def _authorize(self, project_id: str, permission: str = "read") -> None:
        if self.authorization_context is not None:
            self.authorization_context.require(project_id, permission)

    def _project_exists(self, project_id: str) -> bool:
        return self.repository.get_project(project_id) is not None

    @staticmethod
    def _text(value: str, field: str, limit: int, *, required: bool = True) -> str:
        if not isinstance(value, str):
            raise AgentManagerError(f"{field} must be text")
        value = value.strip()
        if (required and not value) or len(value) > limit:
            raise AgentManagerError(f"{field} must contain 1-{limit} characters" if required
                                    else f"{field} must be at most {limit} characters")
        return value

    @classmethod
    def _capabilities(cls, capabilities: list[str] | tuple[str, ...]) -> list[str]:
        if not isinstance(capabilities, (list, tuple)) or len(capabilities) > cls.MAX_CAPABILITIES:
            raise AgentManagerError("capabilities must be a list of at most 32 items")
        cleaned = []
        for item in capabilities:
            value = cls._text(item, "capability", 64)
            if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:-]*", value):
                raise AgentManagerError("capability contains unsupported characters")
            if value not in cleaned:
                cleaned.append(value)
        return sorted(cleaned)

    def register_agent(self, project_id: str, name: str, *,
                       description: str = "", capabilities: list[str] | tuple[str, ...] = ()) -> dict[str, Any]:
        self._authorize(project_id, "write")
        if not self._project_exists(project_id):
            raise KeyError(project_id)
        name = self._text(name, "agent name", 80)
        description = self._text(description, "description", 500, required=False)
        caps = self._capabilities(capabilities)
        now = self.clock()
        agent_id = self._id("agent")
        try:
            with self.db.transaction() as connection:
                connection.execute(
                    """INSERT INTO pc_agents
                       (id,project_id,name,description,capabilities_json,status,created_at,updated_at)
                       VALUES(?,?,?,?,?,'active',?,?)""",
                    (agent_id, project_id, name, description, json.dumps(caps), now, now),
                )
        except Exception as exc:
            # Normalize duplicate-name failures without masking unrelated errors.
            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                raise AgentManagerError("An agent with this name already exists in the project") from exc
            raise
        return self.get_agent(project_id, agent_id)

    def get_agent(self, project_id: str, agent_id: str) -> dict[str, Any] | None:
        self._authorize(project_id, "read")
        with self.db.connection() as connection:
            row = connection.execute(
                "SELECT * FROM pc_agents WHERE project_id=? AND id=?", (project_id, agent_id)
            ).fetchone()
            if row is None:
                return None
            item = dict(row)
            roles = connection.execute(
                "SELECT role FROM pc_agent_roles WHERE project_id=? AND agent_id=? ORDER BY role",
                (project_id, agent_id),
            ).fetchall()
        item["capabilities"] = json.loads(item.pop("capabilities_json"))
        item["roles"] = [r["role"] for r in roles]
        return item

    def list_agents(self, project_id: str, *, include_disabled: bool = False) -> list[dict[str, Any]]:
        self._authorize(project_id, "read")
        with self.db.connection() as connection:
            query = "SELECT id FROM pc_agents WHERE project_id=?"
            if not include_disabled:
                query += " AND status='active'"
            query += " ORDER BY name COLLATE NOCASE"
            rows = connection.execute(query, (project_id,)).fetchall()
        return [self.get_agent(project_id, row["id"]) for row in rows]

    def assign_role(self, project_id: str, agent_id: str, role: str) -> dict[str, Any]:
        self._authorize(project_id, "write")
        if role not in self.ROLES:
            raise AgentManagerError(f"role must be one of: {', '.join(sorted(self.ROLES))}")
        now = self.clock()
        with self.db.transaction() as connection:
            agent = connection.execute(
                "SELECT id FROM pc_agents WHERE project_id=? AND id=? AND status='active'",
                (project_id, agent_id),
            ).fetchone()
            if agent is None:
                raise KeyError(agent_id)
            connection.execute(
                "INSERT INTO pc_agent_roles(agent_id,project_id,role,assigned_at) VALUES(?,?,?,?) "
                "ON CONFLICT(agent_id,role) DO UPDATE SET assigned_at=excluded.assigned_at",
                (agent_id, project_id, role, now),
            )
        return self.get_agent(project_id, agent_id)

    def remove_role(self, project_id: str, agent_id: str, role: str) -> bool:
        self._authorize(project_id, "write")
        with self.db.transaction() as connection:
            cursor = connection.execute(
                "DELETE FROM pc_agent_roles WHERE project_id=? AND agent_id=? AND role=?",
                (project_id, agent_id, role),
            )
        return cursor.rowcount == 1

    def set_agent_status(self, project_id: str, agent_id: str, status: str) -> bool:
        self._authorize(project_id, "write")
        if status not in {"active", "disabled"}:
            raise AgentManagerError("status must be active or disabled")
        with self.db.transaction() as connection:
            cursor = connection.execute(
                "UPDATE pc_agents SET status=?,updated_at=? WHERE project_id=? AND id=?",
                (status, self.clock(), project_id, agent_id),
            )
        return cursor.rowcount == 1

    def select_agent(self, project_id: str, role: str, *,
                     required_capabilities: list[str] | tuple[str, ...] = ()) -> dict[str, Any] | None:
        """Choose a matching active agent using least-used, oldest-selected first."""
        self._authorize(project_id, "read")
        if role not in self.ROLES:
            raise AgentManagerError("Unsupported agent role")
        required = set(self._capabilities(required_capabilities))
        with self.db.connection() as connection:
            rows = connection.execute(
                """SELECT a.* FROM pc_agents a
                   JOIN pc_agent_roles r ON r.agent_id=a.id AND r.project_id=a.project_id
                   WHERE a.project_id=? AND a.status='active' AND r.role=?
                   ORDER BY a.selection_count ASC, COALESCE(a.last_selected_at,'') ASC, a.name ASC""",
                (project_id, role),
            ).fetchall()
        candidates = []
        for row in rows:
            item = dict(row)
            if required.issubset(set(json.loads(item["capabilities_json"]))):
                candidates.append(item)
        if not candidates:
            return None
        chosen = candidates[0]
        selected_at = self.clock()
        with self.db.transaction() as connection:
            cursor = connection.execute(
                """UPDATE pc_agents SET selection_count=selection_count+1,last_selected_at=?
                   WHERE id=? AND project_id=? AND status='active'""",
                (selected_at, chosen["id"], project_id),
            )
            if cursor.rowcount != 1:
                return None
            connection.execute(
                "INSERT INTO pc_agent_selections(id,project_id,agent_id,role,selected_at) VALUES(?,?,?,?,?)",
                (self._id("selection"), project_id, chosen["id"], role, selected_at),
            )
        return self.get_agent(project_id, chosen["id"])

    def send_message(self, project_id: str, sender_agent_id: str, recipient_agent_id: str,
                     payload: dict[str, Any], *, message_type: str = "request") -> dict[str, Any]:
        self._authorize(project_id, "write")
        if message_type not in self.MESSAGE_TYPES:
            raise AgentManagerError("Unsupported message type")
        if sender_agent_id == recipient_agent_id:
            raise AgentManagerError("An agent cannot message itself")
        if not isinstance(payload, dict):
            raise AgentManagerError("message payload must be a JSON object")
        try:
            encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise AgentManagerError("message payload must be JSON serializable") from exc
        if len(encoded.encode("utf-8")) > self.MAX_PAYLOAD_BYTES:
            raise AgentManagerError("message payload exceeds 16384 bytes")
        now, message_id = self.clock(), self._id("message")
        with self.db.transaction() as connection:
            agents = connection.execute(
                "SELECT id FROM pc_agents WHERE project_id=? AND status='active' AND id IN (?,?)",
                (project_id, sender_agent_id, recipient_agent_id),
            ).fetchall()
            if len(agents) != 2:
                raise AgentManagerError("Both sender and recipient must be active agents in this project")
            connection.execute(
                """INSERT INTO pc_agent_messages
                   (id,project_id,sender_agent_id,recipient_agent_id,message_type,payload_json,status,created_at)
                   VALUES(?,?,?,?,?,?,'queued',?)""",
                (message_id, project_id, sender_agent_id, recipient_agent_id, message_type, encoded, now),
            )
        return self.get_message(project_id, message_id)

    def get_message(self, project_id: str, message_id: str) -> dict[str, Any] | None:
        self._authorize(project_id, "read")
        with self.db.connection() as connection:
            row = connection.execute(
                "SELECT * FROM pc_agent_messages WHERE project_id=? AND id=?",
                (project_id, message_id),
            ).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        return item

    def list_messages(self, project_id: str, agent_id: str, *,
                      inbox: bool = True, unread_only: bool = False, limit: int = 50) -> list[dict[str, Any]]:
        self._authorize(project_id, "read")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise AgentManagerError("limit must be between 1 and 200")
        direction = "recipient_agent_id" if inbox else "sender_agent_id"
        query = f"SELECT id FROM pc_agent_messages WHERE project_id=? AND {direction}=?"
        params: list[Any] = [project_id, agent_id]
        if unread_only and inbox:
            query += " AND status='queued'"
        query += " ORDER BY created_at,id LIMIT ?"
        params.append(limit)
        with self.db.connection() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [self.get_message(project_id, row["id"]) for row in rows]

    def mark_message_read(self, project_id: str, recipient_agent_id: str, message_id: str) -> bool:
        self._authorize(project_id, "write")
        with self.db.transaction() as connection:
            cursor = connection.execute(
                """UPDATE pc_agent_messages SET status='read',read_at=?
                   WHERE project_id=? AND recipient_agent_id=? AND id=? AND status='queued'""",
                (self.clock(), project_id, recipient_agent_id, message_id),
            )
        return cursor.rowcount == 1
