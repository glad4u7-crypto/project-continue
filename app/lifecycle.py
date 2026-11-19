"""Explicit, testable application lifecycle state management."""

from enum import Enum
from threading import RLock
from typing import Callable

from core.errors import LifecycleError


class LifecycleState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


class ApplicationLifecycle:
    """Manage one application's start/stop transitions and optional hooks."""

    def __init__(
        self,
        on_start: Callable[[], None] | None = None,
        on_stop: Callable[[], None] | None = None,
    ) -> None:
        self._on_start = on_start
        self._on_stop = on_stop
        self._state = LifecycleState.CREATED
        self._lock = RLock()

    @property
    def state(self) -> LifecycleState:
        return self._state

    def start(self) -> bool:
        """Start once; return False when already running."""
        with self._lock:
            if self._state is LifecycleState.RUNNING:
                return False
            if self._state is not LifecycleState.CREATED:
                raise LifecycleError(
                    f"Cannot start application from {self._state.value} state"
                )
            try:
                if self._on_start is not None:
                    self._on_start()
            except Exception as exc:
                self._state = LifecycleState.FAILED
                raise LifecycleError("Application startup failed") from exc
            self._state = LifecycleState.RUNNING
            return True

    def stop(self) -> bool:
        """Stop once; return False when not running."""
        with self._lock:
            if self._state in {LifecycleState.CREATED, LifecycleState.STOPPED}:
                return False
            if self._state is LifecycleState.FAILED:
                raise LifecycleError("Cannot stop an application that failed")
            try:
                if self._on_stop is not None:
                    self._on_stop()
            except Exception as exc:
                self._state = LifecycleState.FAILED
                raise LifecycleError("Application shutdown failed") from exc
            self._state = LifecycleState.STOPPED
            return True
