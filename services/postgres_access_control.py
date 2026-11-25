"""PostgreSQL identity, session, membership and audit implementation."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from typing import Any

from database.postgres_connection import PostgresDatabase

_ROLES = frozenset({"admin", "owner", "editor", "viewer"})
_EMAIL = re.compile(r"^[^\s@]{1,64}@[^\s@]{1,255}$")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class AccessDenied(PermissionError):
    """Raised when a principal lacks access to a project or operation."""


class PostgresAccessControl:
    """PostgreSQL-backed access control; compatible in intent with SQLite AccessControl."""

    def __init__(self, database: PostgresDatabase, signing_key: str | bytes, *, clock=time.time):
        key = signing_key.encode() if isinstance(signing_key, str) else signing_key
        if not isinstance(key, bytes) or len(key) < 32:
            raise ValueError("SESSION_SIGNING_KEY must contain at least 32 bytes")
        self.database, self._key, self.clock = database, key, clock

    @staticmethod
    def _password(password: str) -> tuple[bytes, bytes]:
        if not isinstance(password, str) or len(password) < 12 or len(password) > 1024:
            raise ValueError("Password must contain 12-1024 characters")
        salt = secrets.token_bytes(16)
        return salt, hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)

    def create_user(self, user_id: str, email: str, password: str, *, role="viewer") -> None:
        if role not in _ROLES:
            raise ValueError("Unsupported role")
        normalized = email.strip().lower() if isinstance(email, str) else ""
        if not _EMAIL.fullmatch(normalized):
            raise ValueError("A valid email address is required")
        salt, digest = self._password(password)
        with self.database.transaction() as c:
            c.execute(
                "INSERT INTO pc_users(id,email,password_salt,password_hash,role,enabled,created_at) "
                "VALUES(%s,%s,%s,%s,%s,1,%s)",
                (user_id, normalized, salt, digest, role, int(self.clock())),
            )

    def _signed_principal(self, row, expires_at: int) -> dict[str, Any]:
        principal = {"id": row["id"], "email": row["email"], "role": row["role"]}
        message = json.dumps([principal["id"], principal["email"], principal["role"], int(expires_at)], separators=(",", ":"))
        proof = _b64(hmac.new(self._key, ("principal:" + message).encode(), hashlib.sha256).digest())
        return {**principal, "_principal_exp": int(expires_at), "_principal_proof": proof}

    def authenticate(self, email: str, password: str) -> dict[str, Any] | None:
        normalized = email.strip().lower() if isinstance(email, str) else ""
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        now = int(self.clock())
        with self.database.connection() as c:
            failures = c.execute(
                "SELECT COUNT(*) AS n FROM pc_login_attempts "
                "WHERE email_digest=%s AND succeeded=0 AND attempted_at>%s",
                (digest, now - 900),
            ).fetchone()["n"]
            row = c.execute(
                "SELECT * FROM pc_users WHERE email=%s AND enabled=1", (normalized,)
            ).fetchone()
        if failures >= 10:
            return None
        if row is None:
            hashlib.scrypt(str(password).encode(), salt=b"project-continue-dummy-salt", n=2**14, r=8, p=1)
            with self.database.transaction() as c:
                c.execute("INSERT INTO pc_login_attempts VALUES(%s,%s,0)", (digest, now))
            return None
        candidate = hashlib.scrypt(str(password).encode(), salt=row["password_salt"], n=2**14, r=8, p=1)
        succeeded = hmac.compare_digest(candidate, row["password_hash"])
        with self.database.transaction() as c:
            c.execute("DELETE FROM pc_login_attempts WHERE attempted_at<%s", (now - 86400,))
            c.execute("INSERT INTO pc_login_attempts VALUES(%s,%s,%s)", (digest, now, int(succeeded)))
            if succeeded:
                c.execute("DELETE FROM pc_login_attempts WHERE email_digest=%s AND succeeded=0", (digest,))
        return self._signed_principal(row, now + 3600) if succeeded else None

    def verify_principal(self, principal: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(principal, dict):
            raise AccessDenied("Verified session principal is required")
        try:
            user_id, email, role = principal["id"], principal["email"], principal["role"]
            expires, proof = int(principal["_principal_exp"]), principal["_principal_proof"]
            if not all(isinstance(v, str) for v in (user_id, email, role)) or expires <= int(self.clock()):
                raise ValueError
            message = json.dumps([user_id, email, role, expires], separators=(",", ":"))
            expected = _b64(hmac.new(self._key, ("principal:" + message).encode(), hashlib.sha256).digest())
            if not isinstance(proof, str) or not hmac.compare_digest(proof, expected):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise AccessDenied("Verified session principal is required") from None
        with self.database.connection() as c:
            row = c.execute("SELECT id,email,role,enabled FROM pc_users WHERE id=%s", (user_id,)).fetchone()
        if row is None or not row["enabled"] or row["email"] != email or row["role"] != role:
            raise AccessDenied("Account is disabled or session is no longer valid")
        return self._signed_principal(row, expires)

    def issue_session(self, principal: dict[str, Any], *, ttl_seconds=3600) -> str:
        if ttl_seconds < 60 or ttl_seconds > 86400:
            raise ValueError("Session lifetime must be 60-86400 seconds")
        principal = self.verify_principal(principal)
        payload = {"sub": principal["id"], "role": principal["role"],
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
                row = c.execute("SELECT id,email,role,enabled FROM pc_users WHERE id=%s", (payload["sub"],)).fetchone()
            if row is None or not row["enabled"] or row["role"] != payload.get("role"):
                return None
            return self._signed_principal(row, int(payload["exp"]))
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def bootstrap_project_owner(self, principal: dict[str, Any], project_id: str) -> None:
        principal = self.verify_principal(principal)
        if principal.get("role") not in {"owner", "admin"}:
            raise AccessDenied("Only an owner or administrator can bootstrap ownership")
        with self.database.transaction() as c:
            if c.execute("SELECT 1 FROM projects WHERE id=%s", (project_id,)).fetchone() is None:
                raise KeyError(project_id)
            if c.execute("SELECT 1 FROM pc_project_memberships WHERE project_id=%s AND role='owner'", (project_id,)).fetchone():
                raise AccessDenied("Project already has an owner")
            account = c.execute("SELECT role,enabled FROM pc_users WHERE id=%s FOR UPDATE", (principal["id"],)).fetchone()
            if account is None or not account["enabled"] or account["role"] != principal["role"]:
                raise AccessDenied("Account is disabled, unavailable, or has an invalid role")
            c.execute("INSERT INTO pc_project_memberships VALUES(%s,%s,'owner',%s)",
                      (project_id, principal["id"], int(self.clock())))
        self._audit(principal["id"], "membership.bootstrap_owner", project_id, "success")

    def grant_project(self, actor: dict[str, Any], project_id: str, user_id: str, *, role="viewer") -> None:
        if role not in {"owner", "editor", "viewer"}:
            raise ValueError("Unsupported project role")
        actor = self.verify_principal(actor)
        self.require_project(actor, project_id, permission="manage")
        if role == "owner" and actor["role"] != "admin":
            raise AccessDenied("Only an administrator may assign project-owner role")
        with self.database.transaction() as c:
            existing = c.execute(
                "SELECT role FROM pc_project_memberships WHERE project_id=%s AND user_id=%s FOR UPDATE",
                (project_id, user_id),
            ).fetchone()
            owner_count = c.execute(
                "SELECT COUNT(*) AS n FROM pc_project_memberships WHERE project_id=%s AND role='owner'",
                (project_id,),
            ).fetchone()["n"]
            if existing and existing["role"] == "owner" and role != "owner" and owner_count <= 1:
                raise AccessDenied("A project must retain at least one owner")
            c.execute(
                "INSERT INTO pc_project_memberships VALUES(%s,%s,%s,%s) "
                "ON CONFLICT(project_id,user_id) DO UPDATE SET role=EXCLUDED.role",
                (project_id, user_id, role, int(self.clock())),
            )
        self._audit(actor["id"], "membership.grant", project_id, "success")

    def require_project(self, principal: dict[str, Any], project_id: str, *, permission="read") -> None:
        if permission not in {"read", "write", "manage"}:
            raise ValueError("Unsupported permission")
        principal = self.verify_principal(principal)
        with self.database.connection() as c:
            user = c.execute("SELECT role,enabled FROM pc_users WHERE id=%s", (principal["id"],)).fetchone()
            project = c.execute("SELECT id FROM projects WHERE id=%s", (project_id,)).fetchone()
            membership = c.execute(
                "SELECT role FROM pc_project_memberships WHERE project_id=%s AND user_id=%s",
                (project_id, principal["id"]),
            ).fetchone()
        allowed = bool(user and user["enabled"] and project and (
            user["role"] == "admin" or membership and (
                permission == "read" or permission == "write" and membership["role"] in {"owner", "editor"}
                or permission == "manage" and membership["role"] == "owner"
            )
        ))
        self._audit(principal["id"], "project." + permission, project_id, "success" if allowed else "denied")
        if not allowed:
            raise AccessDenied("Project access denied")

    def _audit(self, actor_id, action, project_id, outcome):
        with self.database.transaction() as c:
            c.execute(
                "INSERT INTO pc_audit_events(actor_id,action,project_id,outcome,created_at) VALUES(%s,%s,%s,%s,%s)",
                (actor_id, action, project_id, outcome, int(self.clock())),
            )

    def list_audit_events(self, *, limit=100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        with self.database.connection() as c:
            return [dict(r) for r in c.execute(
                "SELECT id,actor_id,action,project_id,outcome,created_at FROM pc_audit_events "
                "ORDER BY id DESC LIMIT %s", (limit,)
            )]
