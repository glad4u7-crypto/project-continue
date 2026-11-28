"""Strict execution lifecycle state machine for dispatcher requests."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class ExecutionState(str, Enum):
    ACK = "ACK"
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class InvalidTransition(ValueError):
    """Raised when a lifecycle transition violates the state graph."""


class StaleStateVersion(InvalidTransition):
    """Raised when a transition is based on a stale state version."""


TERMINAL_STATES = frozenset({
    ExecutionState.PASS,
    ExecutionState.FAIL,
    ExecutionState.BLOCKED,
    ExecutionState.CANCELLED,
})

_ALLOWED_TRANSITIONS = {
    ExecutionState.ACK: frozenset({
        ExecutionState.RUNNING,
        ExecutionState.BLOCKED,
        ExecutionState.CANCELLED,
    }),
    ExecutionState.RUNNING: TERMINAL_STATES,
    ExecutionState.PASS: frozenset(),
    ExecutionState.FAIL: frozenset(),
    ExecutionState.BLOCKED: frozenset(),
    ExecutionState.CANCELLED: frozenset(),
}


@dataclass(frozen=True)
class StateEvent:
    version: int
    previous: ExecutionState | None
    current: ExecutionState
    occurred_at: datetime
    reason: str | None = None


class ExecutionStateMachine:
    """In-memory, versioned state transition aggregate.

    Persistence and cross-worker concurrency are intentionally supplied by a
    later storage integration; this class enforces the domain transition graph.
    """

    def __init__(self, *, now: datetime | None = None) -> None:
        timestamp = now or datetime.now(timezone.utc)
        self._validate_timestamp(timestamp)
        self._state = ExecutionState.ACK
        self._version = 1
        self._events = [
            StateEvent(1, None, ExecutionState.ACK, timestamp, "request accepted")
        ]

    @staticmethod
    def _validate_timestamp(value: datetime) -> None:
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("state timestamps must be timezone-aware")

    @property
    def state(self) -> ExecutionState:
        return self._state

    @property
    def version(self) -> int:
        return self._version

    @property
    def is_terminal(self) -> bool:
        return self._state in TERMINAL_STATES

    @property
    def history(self) -> tuple[StateEvent, ...]:
        return tuple(self._events)

    def transition(
        self,
        target: ExecutionState | str,
        *,
        now: datetime | None = None,
        expected_version: int | None = None,
        reason: str | None = None,
    ) -> StateEvent:
        try:
            next_state = target if isinstance(target, ExecutionState) else ExecutionState(target)
        except (TypeError, ValueError) as exc:
            raise InvalidTransition("unknown execution state") from exc

        if expected_version is not None and expected_version != self._version:
            raise StaleStateVersion(
                f"expected version {expected_version}, current version {self._version}"
            )
        if next_state not in _ALLOWED_TRANSITIONS[self._state]:
            raise InvalidTransition(f"{self._state.value} -> {next_state.value} is not allowed")

        timestamp = now or datetime.now(timezone.utc)
        self._validate_timestamp(timestamp)
        if timestamp < self._events[-1].occurred_at:
            raise InvalidTransition("state event timestamp cannot move backwards")

        if next_state in {ExecutionState.FAIL, ExecutionState.BLOCKED, ExecutionState.CANCELLED}:
            if not isinstance(reason, str) or not reason.strip():
                raise InvalidTransition(f"{next_state.value} requires a non-empty reason")

        event = StateEvent(
            version=self._version + 1,
            previous=self._state,
            current=next_state,
            occurred_at=timestamp,
            reason=reason.strip() if isinstance(reason, str) and reason.strip() else None,
        )
        self._state = next_state
        self._version = event.version
        self._events.append(event)
        return event
