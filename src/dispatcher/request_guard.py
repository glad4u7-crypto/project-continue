"""Fail-closed request envelope validation for the Phase 20 dispatcher."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Mapping, Any
from uuid import UUID
import re

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_ACTOR_ID = re.compile(r"^[0-9]+$")
_IDEMPOTENCY = re.compile(r"^[A-Za-z0-9._:-]{16,128}$")


class RequestRejected(ValueError):
    """Raised when a dispatcher request must be rejected."""


def _utc_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise RequestRejected(f"{field}: required ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise RequestRejected(f"{field}: malformed timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RequestRejected(f"{field}: timezone offset required")
    return parsed.astimezone(timezone.utc)


def validate_and_claim(
    envelope: Mapping[str, Any],
    *,
    now: datetime,
    claim_pair: Callable[[str, str, datetime], bool],
    max_ttl_seconds: int = 300,
) -> None:
    """Validate canonical v1.0 envelope and atomically consume ID + nonce."""
    if not isinstance(envelope, Mapping):
        raise RequestRejected("request: object required")
    required = {
        "schema_version", "request_id", "nonce", "idempotency_key",
        "actor", "repository", "task", "issued_at", "expires_at",
    }
    optional = {"trace_id"}
    if not required.issubset(envelope.keys()) or not set(envelope.keys()).issubset(required | optional):
        raise RequestRejected("request: missing or unexpected fields")
    if envelope["schema_version"] != "1.0":
        raise RequestRejected("schema_version: unsupported")
    try:
        request_id = str(UUID(envelope["request_id"]))
        nonce = str(UUID(envelope["nonce"]))
    except (ValueError, TypeError, AttributeError) as exc:
        raise RequestRejected("request_id/nonce: UUID required") from exc
    if not isinstance(envelope["idempotency_key"], str) or not _IDEMPOTENCY.fullmatch(envelope["idempotency_key"]):
        raise RequestRejected("idempotency_key: invalid")

    actor = envelope["actor"]
    if not isinstance(actor, Mapping) or set(actor) != {"id", "type"}:
        raise RequestRejected("actor: malformed")
    if not isinstance(actor["id"], str) or not _ACTOR_ID.fullmatch(actor["id"]):
        raise RequestRejected("actor.id: decimal string required")
    if actor["type"] != "user":
        raise RequestRejected("actor.type: user required")

    repository = envelope["repository"]
    if not isinstance(repository, Mapping) or set(repository) != {"id", "full_name", "commit_sha"}:
        raise RequestRejected("repository: malformed")
    if type(repository["id"]) is not int or repository["id"] <= 0:
        raise RequestRejected("repository.id: positive integer required")
    if not isinstance(repository["full_name"], str) or repository["full_name"].count("/") != 1:
        raise RequestRejected("repository.full_name: owner/name required")
    if not isinstance(repository["commit_sha"], str) or not _HEX40.fullmatch(repository["commit_sha"]):
        raise RequestRejected("repository.commit_sha: full 40-character SHA required")

    task = envelope["task"]
    if not isinstance(task, Mapping) or set(task) != {"task_id", "arguments"}:
        raise RequestRejected("task: malformed")
    if task["task_id"] not in {"repo.read_file", "repo.list_tree", "tests.run_pytest"}:
        raise RequestRejected("task.task_id: not allow-listed")
    if not isinstance(task["arguments"], Mapping):
        raise RequestRejected("task.arguments: object required")
    if "trace_id" in envelope and (not isinstance(envelope["trace_id"], str) or not 1 <= len(envelope["trace_id"]) <= 128):
        raise RequestRejected("trace_id: invalid")

    issued = _utc_timestamp(envelope["issued_at"], "issued_at")
    expires = _utc_timestamp(envelope["expires_at"], "expires_at")
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise RequestRejected("now: timezone-aware datetime required")
    current = now.astimezone(timezone.utc)
    if issued > current:
        raise RequestRejected("issued_at: future request")
    if expires <= current:
        raise RequestRejected("expires_at: request expired")
    if expires <= issued:
        raise RequestRejected("expires_at: must follow issued_at")
    if (expires - issued).total_seconds() > max_ttl_seconds:
        raise RequestRejected("expires_at: TTL exceeds policy")
    if not claim_pair(request_id, nonce, expires):
        raise RequestRejected("request_id/nonce: duplicate or replay detected")


class RequestGuard:
    """Reusable fail-closed validation boundary backed by a durable replay store."""

    def __init__(self, replay_store: Any, *, max_ttl_seconds: int = 300) -> None:
        claim_pair = getattr(replay_store, "claim_pair", None)
        if not callable(claim_pair):
            raise TypeError("replay_store must provide callable claim_pair")
        if type(max_ttl_seconds) is not int or max_ttl_seconds < 1:
            raise ValueError("max_ttl_seconds must be a positive integer")
        self._claim_pair = claim_pair
        self._max_ttl_seconds = max_ttl_seconds

    def validate(self, envelope: Mapping[str, Any], *, now: datetime) -> None:
        validate_and_claim(
            envelope, now=now, claim_pair=self._claim_pair,
            max_ttl_seconds=self._max_ttl_seconds,
        )
