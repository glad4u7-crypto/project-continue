"""Authenticated, fixed-registry dispatcher orchestration boundary.

All identity/repository/permission/commit resolvers are trusted adapters supplied
by the host. Request-body identity fields are never used as authentication.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Callable, Mapping

from src.dispatcher.request_guard import RequestGuard, RequestRejected


class AuthorizationRejected(PermissionError):
    """Raised when authenticated identity or repository authorization fails."""


class TaskArgumentsRejected(ValueError):
    """Raised when task arguments do not match the fixed task contract."""


def _validate_arguments(schema: Mapping[str, Any], arguments: Mapping[str, Any]) -> None:
    if not isinstance(arguments, Mapping):
        raise TaskArgumentsRejected("arguments must be an object")
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise TaskArgumentsRejected("unsupported or unsafe task schema")
    properties = schema.get("properties")
    required = schema.get("required")
    if not isinstance(properties, Mapping) or not isinstance(required, list):
        raise TaskArgumentsRejected("malformed task schema")
    if set(arguments) - set(properties) or set(required) - set(arguments):
        raise TaskArgumentsRejected("missing or unexpected task arguments")

    for name, value in arguments.items():
        spec = properties[name]
        if not isinstance(value, str):
            raise TaskArgumentsRejected(f"{name}: string required")
        if len(value) < spec.get("minLength", 0) or len(value) > spec.get("maxLength", 100000):
            raise TaskArgumentsRejected(f"{name}: length outside policy")
        if "enum" in spec and value not in spec["enum"]:
            raise TaskArgumentsRejected(f"{name}: value not allow-listed")
        if "pattern" in spec and re.fullmatch(spec["pattern"], value) is None:
            raise TaskArgumentsRejected(f"{name}: pattern mismatch")

    scope = arguments.get("scope")
    if scope == "focused" and "test_path" not in arguments:
        raise TaskArgumentsRejected("focused pytest requires test_path")
    if scope == "full" and "test_path" in arguments:
        raise TaskArgumentsRejected("full pytest forbids test_path")


class SecureDispatcher:
    """Authorize, validate, consume replay claims, then resolve a fixed handler."""

    def __init__(
        self,
        *,
        policy: Mapping[str, Any],
        registry: Mapping[str, Any],
        request_guard: RequestGuard,
        authenticated_identity: Callable[[], Mapping[str, Any]],
        repository_lookup: Callable[[int], Mapping[str, Any]],
        permission_lookup: Callable[[str, str], str | None],
        commit_verifier: Callable[[str, str], bool],
        handlers: Mapping[str, Callable[[Mapping[str, Any], Mapping[str, Any]], Any]],
    ) -> None:
        self.policy = policy
        self.registry = registry
        self.request_guard = request_guard
        self.authenticated_identity = authenticated_identity
        self.repository_lookup = repository_lookup
        self.permission_lookup = permission_lookup
        self.commit_verifier = commit_verifier
        self.handlers = handlers
        if policy.get("default_decision") != "reject":
            raise ValueError("authorization policy must default to reject")
        if registry.get("registry_version") != "1.0":
            raise ValueError("unsupported task registry version")

    def dispatch(self, envelope: Mapping[str, Any], *, now: datetime) -> Any:
        if not isinstance(envelope, Mapping):
            raise RequestRejected("request: object required")

        # Resolve trusted identity independently of all request-supplied claims.
        identity = self.authenticated_identity()
        if not isinstance(identity, Mapping):
            raise AuthorizationRejected("authenticated identity unavailable")
        allowed_actors = self.policy.get("allowed_actors", [])
        actor_rule = next(
            (item for item in allowed_actors
             if str(item.get("id")) == str(identity.get("id"))
             and item.get("login") == identity.get("login")
             and item.get("type") == identity.get("type") == "user"),
            None,
        )
        if actor_rule is None:
            raise AuthorizationRejected("authenticated actor is not allow-listed")
        actor_claim = envelope.get("actor")
        if not isinstance(actor_claim, Mapping) or (
            actor_claim.get("id") != str(identity.get("id"))
            or actor_claim.get("type") != identity.get("type")
        ):
            raise AuthorizationRejected("request actor does not match authenticated identity")

        repository_claim = envelope.get("repository")
        if not isinstance(repository_claim, Mapping):
            raise AuthorizationRejected("repository claim is malformed")
        repo_id = repository_claim.get("id")
        repo_rule = next(
            (item for item in self.policy.get("repository_allowlist", [])
             if item.get("id") == repo_id
             and item.get("full_name") == repository_claim.get("full_name")
             and str(item.get("owner_id")) == str(identity.get("id"))
             and str(item.get("owner_id")) == str(actor_rule.get("id"))),
            None,
        )
        if repo_rule is None:
            raise AuthorizationRejected("repository is not allow-listed")

        live_repo = self.repository_lookup(repo_id)
        if not isinstance(live_repo, Mapping) or (
            live_repo.get("id") != repo_rule["id"]
            or live_repo.get("full_name") != repo_rule["full_name"]
            or str(live_repo.get("owner_id")) != str(repo_rule["owner_id"])
        ):
            raise AuthorizationRejected("live repository identity mismatch")

        task_claim = envelope.get("task")
        if not isinstance(task_claim, Mapping):
            raise RequestRejected("task: malformed")
        task_id = task_claim.get("task_id")
        task_entry = next(
            (item for item in self.registry.get("tasks", [])
             if item.get("task_id") == task_id),
            None,
        )
        if task_entry is None:
            raise AuthorizationRejected("task is not in the fixed registry")
        permission = self.permission_lookup(identity["login"], repo_rule["full_name"])
        required_permission = self.policy.get("task_permission_map", {}).get(task_id)
        permission_levels = {"none": 0, "read": 1, "pull": 1, "triage": 1,
                             "write": 2, "maintain": 3, "admin": 4}
        if (permission not in permission_levels or required_permission not in permission_levels
                or permission_levels[permission] < permission_levels[required_permission]):
            raise AuthorizationRejected("repository permission missing or insufficient")

        commit_sha = repository_claim.get("commit_sha")
        if not isinstance(commit_sha, str) or not self.commit_verifier(repo_rule["full_name"], commit_sha):
            raise AuthorizationRejected("commit SHA is not verified in the allowed repository")

        arguments = task_claim.get("arguments")
        _validate_arguments(task_entry.get("arguments_schema", {}), arguments)

        # Claim request ID + nonce only after authorization and argument checks,
        # but before handler lookup or invocation.
        self.request_guard.validate(envelope, now=now)

        handler_ref = task_entry.get("handler_ref")
        handler = self.handlers.get(handler_ref)
        if not callable(handler):
            raise RuntimeError("fixed task handler is unavailable")
        return handler(envelope, arguments)
