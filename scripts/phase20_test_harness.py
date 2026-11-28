"""Bounded compile/test harness with structured results and conservative retries."""
from __future__ import annotations

import argparse
import json
import importlib.util
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
TIMEOUT_SECONDS = 600
MAX_STREAM_BYTES = 32 * 1024
MAX_RETRIES = 1
SUMMARY = re.compile(r"(?P<passed>\d+) passed|(?P<failed>\d+) failed|(?P<skipped>\d+) skipped|(?P<errors>\d+) errors?")
SECRET_PATTERNS = (
    re.compile(r"(?i)(token|password|secret|api[_-]?key)(\s*[=:]\s*)[^\s,;]+"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
)

@dataclass(frozen=True)
class TaskResult:
    task: str
    status: str
    failure_class: str
    exit_code: int
    duration_seconds: float
    passed: int
    failed: int
    skipped: int
    errors: int
    attempts: int
    stdout: str
    stderr: str
    retryable: bool


def _redact(value: str) -> str:
    for pattern in SECRET_PATTERNS:
        value = pattern.sub(lambda m: (m.group(1) + m.group(2) + "[REDACTED]") if m.lastindex else "[REDACTED]", value)
    return value


def _bounded(data: str) -> str:
    encoded = data.encode("utf-8", errors="replace")
    if len(encoded) <= MAX_STREAM_BYTES:
        return _redact(data)
    return _redact(encoded[:MAX_STREAM_BYTES].decode("utf-8", errors="replace")) + "\n[output truncated]"


def build_command(task: str) -> tuple[str, ...] | None:
    """Map a fixed task ID to immutable argv; never accept shell fragments."""
    py = sys.executable
    if task == "baseline":
        return (py, "-c", "import importlib.metadata as m, json, platform, sys; print(json.dumps({'python': sys.version, 'platform': platform.platform(), 'packages': sorted(d.metadata.get('Name', 'unknown') + '==' + d.version for d in m.distributions())}, sort_keys=True))")
    if task == "compile":
        return (py, "-m", "compileall", "-q", "app", "config.py", "core", "database", "integrations", "services", "src", "scripts", "tests")
    if task == "focused":
        return (py, "-m", "pytest", "-q", "tests/test_dispatcher_admission.py", "tests/test_dispatcher_audit_log.py", "tests/test_dispatcher_execution_state.py", "tests/test_dispatcher_request_guard.py", "tests/test_dispatcher_repository_guard.py", "tests/test_dispatcher_runtime.py", "tests/test_phase20_runner.py", "tests/test_phase20_test_harness.py")
    if task == "full":
        return (py, "-m", "pytest", "-q")
    if task == "lint":
        if importlib.util.find_spec("ruff") is None:
            return None
        return (py, "-m", "ruff", "check", "app", "config.py", "core", "database", "integrations", "services", "src", "tests")
    if task == "failure-probe":
        return (py, "-c", "raise AssertionError('phase20 intentional failure probe')")
    raise ValueError("task is not allow-listed")


def classify(exit_code: int, stdout: str, stderr: str, timed_out: bool = False) -> tuple[str, bool]:
    if timed_out:
        return "timeout", True
    combined = (stdout + "\n" + stderr).lower()
    if exit_code == 0:
        return "none", False
    if any(s in combined for s in ("temporary failure in name resolution", "connection reset", "service unavailable", "502 bad gateway", "503 service unavailable")):
        return "infrastructure", True
    if any(s in combined for s in ("permission denied", "operation not permitted", "access is denied")):
        return "permission", False
    if any(s in combined for s in ("no module named", "modulenotfounderror", "could not find a version", "distribution not found")):
        return "dependency", False
    if any(s in combined for s in ("no space left on device", "runner lost", "unexpected end of file")):
        return "infrastructure", True
    if "syntaxerror" in combined or "assertionerror" in combined or "failed" in combined:
        return "code", False
    return "environment", False


def _counts(stdout: str, stderr: str) -> tuple[int, int, int, int]:
    text = stdout + "\n" + stderr
    totals = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    for line in text.splitlines():
        if " passed" in line or " failed" in line or " skipped" in line or " errors" in line:
            for match in SUMMARY.finditer(line):
                for key, value in match.groupdict().items():
                    if value is not None:
                        totals[key] += int(value)
    return totals["passed"], totals["failed"], totals["skipped"], totals["errors"]


def run_task(task: str, retries: int = 0) -> TaskResult:
    if not isinstance(retries, int) or retries < 0 or retries > MAX_RETRIES:
        raise ValueError("retries must be 0 or 1")
    command = build_command(task)
    if command is None:
        return TaskResult(task, "SKIPPED", "not-installed", 0, 0.0, 0, 0, 0, 0, 0,
                          "", "Optional lint tool ruff is not installed; no dependency was added.", False)
    if task == "failure-probe":
        retries = 0
    environment = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""),
                   "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
    started = time.monotonic()
    stdout = stderr = ""
    code = 0
    failure_class = "none"
    attempts = 0
    timed_out = False
    while True:
        attempts += 1
        try:
            completed = subprocess.run(command, cwd=ROOT, env=environment, shell=False,
                                       capture_output=True, text=True, encoding="utf-8",
                                       errors="replace", timeout=TIMEOUT_SECONDS, check=False)
            stdout, stderr, code = completed.stdout, completed.stderr, completed.returncode
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            stderr += "\nTask exceeded the fixed 600-second timeout."
            code, timed_out = 124, True
        failure_class, retryable = classify(code, stdout, stderr, timed_out)
        if not retryable or attempts > retries:
            break
    duration = round(time.monotonic() - started, 3)
    passed, failed, skipped, errors = _counts(stdout, stderr)
    expected_probe = task == "failure-probe" and failure_class == "code" and code != 0
    status = "EXPECTED_FAILURE_DETECTED" if expected_probe else ("PASS" if code == 0 else "FAIL")
    if expected_probe:
        failure_class = "intentional-code-failure"
    return TaskResult(task, status, failure_class, 0 if expected_probe else code, duration,
                      passed, failed, skipped, errors, attempts, _bounded(stdout), _bounded(stderr),
                      retryable and attempts > retries)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a bounded, allow-listed Project Continue validation task")
    parser.add_argument("task", choices=("baseline", "compile", "focused", "full", "lint", "failure-probe"))
    parser.add_argument("--retries", type=int, default=0, choices=(0, 1))
    args = parser.parse_args(argv)
    result = run_task(args.task, args.retries)
    print(json.dumps(asdict(result), sort_keys=True))
    return 0 if result.status in ("PASS", "SKIPPED", "EXPECTED_FAILURE_DETECTED") else result.exit_code or 1


if __name__ == "__main__":
    raise SystemExit(main())
