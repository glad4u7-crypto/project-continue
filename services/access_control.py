"""SQLite-backed identities, signed sessions, project membership and audit events.

This module is a server-side enforcement primitive. UI hiding is not authorization.
Use a high-entropy SESSION_SIGNING_KEY from the host secret manager (32+ bytes).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import time
from typing import Any

from database.connection import Database


_ROLES = frozenset({"admin", "owner", "editor", "viewer"})
_EMAIL = re.compile(r"^[^\s@]{1,64}@[^\s@]{1,255}$")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class AccessDenied(PermissionError):
    """Raised when a principal lacks access to a project or operation."""


class AccessControl:
    """Identity and authorization store sharing the application's SQLite DB."""

    def __init__(self, database: Database, signing_key: str | bytes, *, clock=time.time):
        key = signing_key.encode() if isinstance(signing_key, str) else signing_key
        if not isinstance(key, bytes) or len(key) < 32:
            raise ValueError("SESSION_SIGNING_KEY must contain at least 32 bytes")
        self.database, self._key, self.clock = database, key, clock
        with database.connection() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS pc_users(
              id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
              password_salt BLOB NOT NULL, password_hash BLOB NOT NULL,
              role TEXT NOT NULL CHECK(role IN ('admin','owner','editor','viewer')),
              enabled INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pc_project_memberships(
              project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES pc_users(id) ON DELETE CASCADE,
              role TEXT NOT NULL CHECK(role IN ('owner','editor','viewer')),
              created_at INTEGER NOT NULL, PRIMARY KEY(project_id,user_id)
            );
            CREATE TABLE IF NOT EXISTS pc_audit_events(
              id INTEGER PRIMARY KEY AUTOINCREMENT, actor_id TEXT,
              action TEXT NOT NULL, project_id TEXT, outcome TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_pc_audit_created ON pc_audit_events(created_at);
            """)

    @staticmethod
    def _password(password: str) -> tuple[bytes, bytes]:
        if not isinstance(password, str) or len(password) < 12 or len(password) > 1024:
            raise ValueError("Password must contain 12-1024 characters")
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
        return salt, digest

    def create_user(self, user_id: str, email: str, password: str, *, role="viewer") -> None:
        if role not in _ROLES:
            raise ValueError("Unsupported role")
        if role != "admin" and role not in {"owner", "editor", "viewer"}:
            raise ValueError("Unsupported role")
        normalized = email.strip().lower() if isinstance(email, str) else ""
        if not _EMAIL.fullmatch(normalized):
            raise ValueError("A valid email address is required")
        salt, digest = self._password(password)
        with self.database.transaction() as c:
            c.execute("INSERT INTO pc_users VALUES(?,?,?,?,?,1,?)",
                      (user_id, normalized, salt, digest, role, int(self.clock())))

    def authenticate(self, email: str, password: str) -> dict[str, Any] | None:
        normalized = email.strip().lower() if isinstance(email, str) else ""
        with self.database.connection() as c:
            row = c.execute("SELECT * FROM pc_users WHERE email=? AND enabled=1",
                            (normalized,)).fetchone()
        if row is None:
            hashlib.scrypt(str(password).encode(), salt=b"project-continue-dummy-salt", n=2**14, r=8, p=1)
            return None
        candidate = hashlib.scrypt(str(password).encode(), salt=row["password_salt"], n=2**14, r=8, p=1)
        if not hmac.compare_digest(candidate, row["password_hash"]):
            return None
        return {"id": row["id"], "email": row["email"], "role": row["role"]}

    def issue_session(self, principal: dict[str, Any], *, ttl_seconds=3600) -> str:
        if ttl_seconds < 60 or ttl_seconds > 86400:
            raise ValueError("Session lifetime must be 60-86400 seconds")
        with self.database.connection() as c:
            row = c.execute("SELECT id,role,enabled FROM pc_users WHERE id=?",
                            (principal.get("id"),)).fetchone()
        if row is None or not row["enabled"]:
            raise AccessDenied("Account is disabled or unavailable")
        payload = {"sub": row["id"], "role": row["role"],
                   "iat": int(self.clock()), "exp": int(self.clock()) + ttl_seconds,
                   "nonce": _b64(secrets.token_bytes(12))}
        body = _b64(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
        signature = _b64(hmac.new(self._key, body.encode(), hashlib.sha256).digest())
        return body + "." + signature

    def verify_session(self, token: str) -> dict[str, Any] | None:
        try:
            body, signature = token.split(".", 1)
            expected = _b64(hmac.new(self._key, body.encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(signature, expected):
                return None
            payload = json.loads(_unb64(body))
            now = int(self.clock())
            if not isinstance(payload.get("sub"), str) or payload.get("exp", 0) <= now or payload.get("iat", now + 1) > now:
                return None
            with self.database.connection() as c:
                row = c.execute("SELECT id,email,role,enabled FROM pc_users WHERE id=?",
                                (payload["sub"],)).fetchone()
            if row is None or not row["enabled"] or row["role"] != payload.get("role"):
                return None
            return {"id": row["id"], "email": row["email"], "role": row["role"]}
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def grant_project(self, actor: dict[str, Any], project_id: str, user_id: str, *, role="viewer") -> None:
        if role not in {"owner", "editor", "viewer"}:
            raise ValueError("Unsupported project role")
        self.require_project(actor, project_id, permission="manage")
        with self.database.transaction() as c:
            c.execute("INSERT INTO pc_project_memberships VALUES(?,?,?,?) "
                      "ON CONFLICT(project_id,user_id) DO UPDATE SET role=excluded.role",
                      (project_id, user_id, role, int(self.clock())))
        self._audit(actor["id"], "membership.grant", project_id, "success")

    def require_project(self, principal: dict[str, Any], project_id: str, *, permission="read") -> None:
        if permission not in {"read", "write", "manage"}:
            raise ValueError("Unsupported permission")
        with self.database.connection() as c:
            user = c.execute("SELECT role,enabled FROM pc_users WHERE id=?",
                             (principal.get("id"),)).fetchone()
            project = c.execute("SELECT id FROM projects WHERE id=?", (project_id,)).fetchone()
            membership = c.execute(
                "SELECT role FROM pc_project_memberships WHERE project_id=? AND user_id=?",
                (project_id, principal.get("id"))).fetchone()
        allowed = False
        if user is not None and user["enabled"] and project is not None:
            if user["role"] == "admin":
                allowed = True
            elif membership is not None:
                role = membership["role"]
                allowed = (permission == "read" or
                           permission == "write" and role in {"owner", "editor"} or
                           permission == "manage" and role == "owner")
        self._audit(principal.get("id"), "project." + permission, project_id,
                    "success" if allowed else "denied")
        if not allowed:
            raise AccessDenied("Project access denied")

    def _audit(self, actor_id, action, project_id, outcome):
        with self.database.transaction() as c:
            c.execute("INSERT INTO pc_audit_events(actor_id,action,project_id,outcome,created_at) VALUES(?,?,?,?,?)",
                      (actor_id, action, project_id, outcome, int(self.clock())))

    def list_audit_events(self, *, limit=100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        with self.database.connection() as c:
            return [dict(r) for r in c.execute(
                "SELECT id,actor_id,action,project_id,outcome,created_at FROM pc_audit_events "
                "ORDER BY id DESC LIMIT ?", (limit,))]
