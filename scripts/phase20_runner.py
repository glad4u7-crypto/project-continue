"""Ephemeral Phase 20 runner exposing only fixed, bounded repository tasks.

No caller-provided command, shell fragment, interpreter flag or arbitrary path is
accepted. The GitHub Actions job supplies one exact task identifier.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TASK_TIMEOUT_SECONDS = 600

_DISPATCHER_TESTS = (
    "tests/test_dispatcher_admission.py",
    "tests/test_dispatcher_audit_log.py",
    "tests/test_dispatcher_execution_state.py",
    "tests/test_dispatcher_request_guard.py",
    "tests/test_dispatcher_runtime.py",
)


def build_command(task: str) -> tuple[str, ...]:
    """Return the immutable argv for one allow-listed task."""
    python = sys.executable
    if task == "compile":
        return (python, "-m", "compileall", "-q", "app", "config.py", "core",
                "database", "integrations", "services", "src", "tests")
    if task == "dispatcher-tests":
        return (python, "-m", "pytest", "-q", *_DISPATCHER_TESTS)
    if task == "full-tests":
        return (python, "-m", "pytest", "-q")
    raise ValueError("task is not allow-listed")


def run_task(task: str) -> int:
    """Run a fixed task in a disposable HOME with no inherited credentials."""
    command = build_command(task)
    with tempfile.TemporaryDirectory(prefix="project-continue-runner-") as home:
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": home,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }
        try:
            completed = subprocess.run(
                command,
                cwd=REPOSITORY_ROOT,
                env=environment,
                timeout=TASK_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            print(f"RUNNER TIMEOUT: task={task} limit={TASK_TIMEOUT_SECONDS}s", file=sys.stderr)
            return 124
    return int(completed.returncode)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one fixed Project Continue task")
    parser.add_argument("task", choices=("compile", "dispatcher-tests", "full-tests"))
    args = parser.parse_args(argv)
    return run_task(args.task)


if __name__ == "__main__":
    raise SystemExit(main())
