"""Ephemeral Phase 20 runner exposing only fixed, bounded repository tasks.

No caller-provided command, shell fragment, interpreter flag or arbitrary path is
accepted. Output, wall time and inherited environment are bounded.
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TASK_TIMEOUT_SECONDS = 600
MAX_OUTPUT_BYTES = 64 * 1024
_OUTPUT_CHUNK_BYTES = 8192

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


def _emit_bounded_output(output: bytearray, total_bytes: int) -> None:
    if output:
        sys.stdout.write(output.decode("utf-8", errors="replace"))
        if not output.endswith(b"\n"):
            sys.stdout.write("\n")
    if total_bytes > MAX_OUTPUT_BYTES:
        print(f"[runner output truncated: retained {MAX_OUTPUT_BYTES} of {total_bytes} bytes]")
    sys.stdout.flush()


def run_task(task: str) -> int:
    """Run a fixed task in a disposable HOME, bounded output and no credentials."""
    command = build_command(task)
    with tempfile.TemporaryDirectory(prefix="project-continue-runner-") as home:
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": home,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }
        process = subprocess.Popen(
            command,
            cwd=REPOSITORY_ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
            start_new_session=True,
        )
        output = bytearray()
        total_bytes = 0

        def drain_output() -> None:
            nonlocal total_bytes
            assert process.stdout is not None
            while True:
                chunk = process.stdout.read(_OUTPUT_CHUNK_BYTES)
                if not chunk:
                    break
                total_bytes += len(chunk)
                remaining = MAX_OUTPUT_BYTES - len(output)
                if remaining > 0:
                    output.extend(chunk[:remaining])

        reader = threading.Thread(target=drain_output, name="phase20-runner-output", daemon=True)
        reader.start()
        timed_out = False
        try:
            return_code = process.wait(timeout=TASK_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            return_code = process.wait()
        finally:
            reader.join()
            if process.stdout is not None:
                process.stdout.close()
        _emit_bounded_output(output, total_bytes)
        if timed_out:
            print(f"RUNNER TIMEOUT: task={task} limit={TASK_TIMEOUT_SECONDS}s", file=sys.stderr)
            return 124
        return int(return_code)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one fixed Project Continue task")
    parser.add_argument("task", choices=("compile", "dispatcher-tests", "full-tests"))
    args = parser.parse_args(argv)
    return run_task(args.task)


if __name__ == "__main__":
    raise SystemExit(main())
