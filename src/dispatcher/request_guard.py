"""Fail-closed request envelope validation for the Phase 20 dispatcher."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Mapping, Any
from uuid import UUID
import re

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_ACTOR_ID = re.compile(r"^[0-9]+$")


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
    """Validate request and atomically consume request ID + nonce.

    claim_pair must durably and atomically claim both values in shared storage.
    It must return False if either value has already been consumed. Storage
    errors propagate so the caller can fail closed.
    """
    if not isinstance(envelope, Mapping):
        raise RequestRejected("request: object required")
    required = {
        "schema_version", "request_id", "nonce", "issued_at", "expires_at",
        "actor", "repository", "commit_sha", "task",
    }
    if set(envelope.keys()) != required:
        raise RequestRejected("request: missing or unexpected fields")
    if envelope["schema_version"] != "1":
        raise RequestRejected("schema_version: unsupported")
    try:
        request_id = str(UUID(envelope["request_id"]))
        nonce = str(UUID(envelope["nonce"]))
    except (ValueError, TypeError, AttributeError) as exc:
        raise RequestRejected("request_id/nonce: UUID required") from exc

    actor = envelope["actor"]
    if not isinstance(actor, Mapping) or set(actor) != {"id", "type"}:
        raise RequestRejected("actor: malformed")
    if not isinstance(actor["id"], str) or not _ACTOR_ID.fullmatch(actor["id"]):
        raise RequestRejected("actor.id: decimal string required")
    if actor["type"] != "user":
        raise RequestRejected("actor.type: user required")

    repository = envelope["repository"]
    if not isinstance(repository, Mapping) or set(repository) != {"id", "full_name"}:
        raise RequestRejected("repository: malformed")
    if type(repository["id"]) is not int or repository["id"] <= 0:
        raise RequestRejected("repository.id: positive integer required")
    if not isinstance(repository["full_name"], str) or repository["full_name"].count("/") != 1:
        raise RequestRejected("repository.full_name: owner/name required")
    if not isinstance(envelope["commit_sha"], str) or not _HEX40.fullmatch(envelope["commit_sha"]):
        raise RequestRejected("commit_sha: full 40-character SHA required")
    if envelope["task"] not in {"repo.read_file", "repo.list_tree", "tests.run_pytest"}:
        raise RequestRejected("task: not allow-listed")

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
