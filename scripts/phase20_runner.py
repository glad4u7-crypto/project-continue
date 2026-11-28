"""Ephemeral Phase 20 runner exposing fixed, bounded repository tasks.

Commands are allow-listed; output, wall time, retries and inherited environment
are bounded. A machine-readable result is emitted for every execution.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import resource
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TASK_TIMEOUT_SECONDS = 600
MAX_OUTPUT_BYTES = 64 * 1024
MAX_RETRIES = 1
_DISPATCHER_TESTS = (
    "tests/test_dispatcher_admission.py",
    "tests/test_dispatcher_audit_log.py",
    "tests/test_dispatcher_execution_state.py",
    "tests/test_dispatcher_request_guard.py",
    "tests/test_dispatcher_repository_guard.py",
    "tests/test_dispatcher_runtime.py",
)


def build_command(task: str) -> tuple[str, ...]:
    """Return immutable argv for one allow-listed task."""
    python = sys.executable
    if task == "compile":
        return (python, "-m", "compileall", "-q", "app", "config.py", "core",
                "database", "integrations", "services", "src", "tests")
    if task == "dispatcher-tests":
        return (python, "-m", "pytest", "-q", *_DISPATCHER_TESTS)
    if task == "full-tests":
        return (python, "-m", "pytest", "-q")
    raise ValueError("task is not allow-listed")


def _read_bounded(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    return data[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"), len(data)


def parse_test_counts(output: str) -> dict[str, int]:
    """Parse pytest quiet and verbose summaries, including separator padding."""
    counts: dict[str, int] = {}
    pattern = r"(\d+)\s+(subtests passed|passed|failed|errors?|skipped|xfailed|xpassed|deselected)"
    for line in output.splitlines():
        # Pytest's verbose terminal reporter surrounds its summary with '='
        # characters; quiet mode does not. Normalize both before parsing.
        candidate = line.strip().strip("=").strip()
        if not re.search(r"\bin\s+[0-9.]+s\s*$", candidate):
            continue
        if not re.search(pattern, candidate):
            continue
        for count, label in re.findall(pattern, candidate):
            key = "subtests_passed" if label == "subtests passed" else (
                "errors" if label in ("error", "errors") else label
            )
            counts[key] = counts.get(key, 0) + int(count)
    return counts


def classify_failure(task: str, return_code: int, stdout: str, stderr: str, timed_out: bool = False) -> str:
    """Classify failures conservatively; unknown failures remain infrastructure."""
    if return_code == 0 and not timed_out:
        return "success"
    if timed_out or return_code == 124:
        return "timeout"
    text = (stdout + "\n" + stderr).lower()
    if any(token in text for token in ("permission denied", "operation not permitted", "access is denied")):
        return "permission"
    if any(token in text for token in ("no module named", "modulenotfounderror", "could not find a version", "no matching distribution")):
        return "dependency"
    if any(token in text for token in ("syntaxerror", "indentationerror", "assertionerror", "failed", "error during collection")):
        return "code"
    if any(token in text for token in ("connection reset", "temporary failure", "network is unreachable", "service unavailable")):
        return "environment"
    return "infrastructure"


def _apply_child_limits() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (TASK_TIMEOUT_SECONDS, TASK_TIMEOUT_SECONDS + 10))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _run_once(task: str) -> dict[str, object]:
    command = build_command(task)
    started = time.monotonic()
    timed_out = False
    spawn_error = ""
    with tempfile.TemporaryDirectory(prefix="project-continue-runner-") as home:
        out_path, err_path = Path(home) / "stdout.log", Path(home) / "stderr.log"
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": home,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }
        try:
            with out_path.open("wb") as out, err_path.open("wb") as err:
                process = subprocess.Popen(
                    command, cwd=REPOSITORY_ROOT, env=environment,
                    stdout=out, stderr=err, shell=False, start_new_session=True,
                    preexec_fn=_apply_child_limits,
                )
                try:
                    return_code = int(process.wait(timeout=TASK_TIMEOUT_SECONDS))
                except subprocess.TimeoutExpired:
                    timed_out = True
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                    return_code = 124
        except OSError as exc:
            return_code = 127
            spawn_error = f"{type(exc).__name__}: {exc}"
        stdout, stdout_total = _read_bounded(out_path) if out_path.exists() else ("", 0)
        stderr, stderr_total = _read_bounded(err_path) if err_path.exists() else ("", 0)

    duration = round(time.monotonic() - started, 3)
    if spawn_error:
        stderr = (stderr + "\n" + spawn_error).strip()
    classification = classify_failure(task, return_code, stdout, stderr, timed_out)
    return {
        "task": task, "exit_code": return_code, "duration_seconds": duration,
        "classification": classification, "timed_out": timed_out,
        "stdout": stdout, "stderr": stderr,
        "stdout_bytes_total": stdout_total, "stderr_bytes_total": stderr_total,
        "stdout_truncated": stdout_total > MAX_OUTPUT_BYTES,
        "stderr_truncated": stderr_total > MAX_OUTPUT_BYTES,
        "test_counts": parse_test_counts(stdout + "\n" + stderr),
    }


def run_task(task: str, retries: int = 0) -> int:
    """Run once; permit at most one retry, only for transient infrastructure failures."""
    if retries < 0 or retries > MAX_RETRIES:
        raise ValueError("retry count exceeds the fixed safety limit")
    attempts = []
    for attempt in range(retries + 1):
        result = _run_once(task)
        attempts.append(result)
        print("PHASE20_ATTEMPT_JSON=" + json.dumps(result, sort_keys=True))
        if result["classification"] == "success":
            break
        if result["classification"] != "infrastructure" or attempt >= retries:
            break
    final = attempts[-1]
    summary = {
        "task": task, "status": final["classification"],
        "exit_code": final["exit_code"], "attempts": len(attempts),
        "retry_limit": retries, "duration_seconds_total": round(
            sum(float(x["duration_seconds"]) for x in attempts), 3
        ),
        "test_counts": final["test_counts"],
    }
    print("PHASE20_RESULT_JSON=" + json.dumps(summary, sort_keys=True))
    for key in ("stdout", "stderr"):
        value = str(final[key])
        if value:
            print(f"--- {key.upper()} (bounded) ---")
            print(value)
    for key in ("stdout_truncated", "stderr_truncated"):
        if final[key]:
            print(f"WARNING: {key} (maximum {MAX_OUTPUT_BYTES} bytes per stream)")
    return int(final["exit_code"])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one fixed Project Continue task")
    parser.add_argument("task", choices=("compile", "dispatcher-tests", "full-tests"))
    parser.add_argument("--retry-transient", action="store_true",
                        help="allow one retry only for infrastructure-classified failures")
    args = parser.parse_args(argv)
    return run_task(args.task, retries=1 if args.retry_transient else 0)


if __name__ == "__main__":
    raise SystemExit(main())
