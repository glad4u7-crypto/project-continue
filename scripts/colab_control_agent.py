"""Bounded GitHub issue command bridge; fixed diagnostics only, never a remote shell."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scripts.colab_dashboard_status import check_local_streamlit

REPOSITORY = "glad4u7-crypto/project-continue"
API_ROOT = f"https://api.github.com/repos/{REPOSITORY}"
AUTHORIZED_LOGIN = "glad4u7-crypto"
COMMAND_RE = re.compile(r"^/pc-run (phase18-tests|compile|dashboard-health|git-status)$")
READ_COMMAND_RE = re.compile(r"^/pc-read (README\.md|app\.py|scripts/colab_control_agent\.py|docs/PHASE-18-COLAB-CONTROL-AGENT\.md)$")
MAX_READ_BYTES = 12000
STATE_PATH = Path(os.environ.get("PROJECT_CONTINUE_AGENT_STATE", "/content/.project_continue_agent_state.json"))
REPO_ROOT = Path(__file__).resolve().parents[1]
TASKS = {
    "phase18-tests": [
        sys.executable, "-m", "pytest", "-q",
        "tests/test_dashboard_health_check.py",
        "tests/test_colab_dashboard_status.py",
        "tests/test_colab_control_agent.py",
    ],
    "compile": [
        sys.executable, "-m", "compileall", "-q",
        "app.py", "core", "database", "integrations", "services", "ui", "scripts",
    ],
    "git-status": ["git", "status", "--short", "--branch"],
}


def get_token() -> str:
    token = os.environ.get("PROJECT_CONTINUE_CONTROL_TOKEN", "").strip()
    if token:
        return token
    try:
        from google.colab import userdata
        return str(userdata.get("PROJECT_CONTINUE_CONTROL_TOKEN") or "").strip()
    except Exception:
        return ""


def api_request(token: str, method: str, url: str, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Project-Continue-Colab-Control-Agent/1.0",
        },
    )
    with urlopen(request, timeout=15) as response:
        raw = response.read(1_000_000)
        return json.loads(raw.decode("utf-8")) if raw else None


def load_state() -> dict:
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {"last_comment_id": 0}
    except (OSError, ValueError):
        return {"last_comment_id": 0}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = STATE_PATH.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(state), encoding="utf-8")
    temporary_path.replace(STATE_PATH)


def run_task(task: str) -> tuple[bool, str]:
    if task == "dashboard-health":
        return check_local_streamlit()
    command = TASKS.get(task)
    if command is None:
        return False, "Task is not allow-listed."
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=600 if task == "phase18-tests" else 120,
            check=False,
            shell=False,
            env={**os.environ, "CI": "1", "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except subprocess.TimeoutExpired:
        return False, "Task timed out; no retry was started."
    output = (result.stdout + "\n" + result.stderr).strip()
    return result.returncode == 0, (
        f"Exit code: {result.returncode}\n{output[-3500:] or '(no output)'}"
    )



def read_project_file(relative_path: str) -> tuple[bool, str]:
    """Read only a small, explicitly allow-listed project text file."""
    allowed = {
        "README.md",
        "app.py",
        "scripts/colab_control_agent.py",
        "docs/PHASE-18-COLAB-CONTROL-AGENT.md",
    }
    if relative_path not in allowed:
        return False, "File path is not allow-listed."
    root = REPO_ROOT.resolve()
    target = (root / relative_path).resolve()
    if root not in target.parents or target.is_symlink() or not target.is_file():
        return False, "File is unavailable or outside the project directory."
    try:
        if target.stat().st_size > MAX_READ_BYTES:
            return False, "File exceeds the 12 KB read limit."
        content = target.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False, "File could not be read as UTF-8 text."
    return True, f"File: {relative_path}\n\n{content[:MAX_READ_BYTES]}"


def process_comments(token: str, issue_number: int, state: dict) -> int:
    """Process all newly-created comments, not just GitHub's first 100."""
    last_id = int(state.get("last_comment_id", 0))
    processed = 0
    page = 1
    while True:
        comments = api_request(
            token,
            "GET",
            f"{API_ROOT}/issues/{issue_number}/comments?per_page=100&page={page}",
        )
        if not isinstance(comments, list):
            raise ValueError("Unexpected GitHub comment list.")
        if not comments:
            break
        for comment in comments:
            comment_id = int(comment.get("id", 0))
            if comment_id <= last_id:
                continue
            author = (comment.get("user") or {}).get("login", "")
            body = str(comment.get("body") or "").strip()
            match = COMMAND_RE.fullmatch(body)
            read_match = READ_COMMAND_RE.fullmatch(body)
            if author == AUTHORIZED_LOGIN and (match or read_match):
                if read_match:
                    task = "read-file"
                    passed, detail = read_project_file(read_match.group(1))
                else:
                    task = match.group(1)
                    passed, detail = run_task(task)
                report = (
                    f"Colab Control Agent: {'PASS' if passed else 'FAIL'}\n"
                    f"Request: {comment_id}\n"
                    f"Task: {task}\n\n"
                    f"{detail[:3500]}\n\n"
                    "Arbitrary shell, source edits, restart, deployment and deletion "
                    "are unsupported."
                )
                api_request(
                    token,
                    "POST",
                    f"{API_ROOT}/issues/{issue_number}/comments",
                    {"body": report},
                )
                processed += 1
            # Persist every seen comment so ignored comments are not rescanned.
            last_id = comment_id
            state["last_comment_id"] = last_id
            save_state(state)
        if len(comments) < 100:
            break
        page += 1
    return processed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--issue",
        type=int,
        default=int(os.environ.get("PROJECT_CONTINUE_CONTROL_ISSUE", "0")),
    )
    parser.add_argument("--interval-seconds", type=int, default=0)
    args = parser.parse_args(argv)
    if args.issue <= 0 or (
        args.interval_seconds != 0 and not 15 <= args.interval_seconds <= 86400
    ):
        print("FAIL: positive issue number and interval 0 or 15-86400 required.")
        return 2
    token = get_token()
    if not token:
        print("FAIL: configure PROJECT_CONTINUE_CONTROL_TOKEN in Colab Secrets.")
        return 2
    state = load_state()
    try:
        while True:
            count = process_comments(token, args.issue, state)
            print(f"Control poll complete; {count} task(s) executed.")
            if args.interval_seconds == 0:
                return 0
            time.sleep(args.interval_seconds)
    except KeyboardInterrupt:
        print("Agent stopped; Colab runtime and Streamlit were not stopped.")
        return 0
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        print(f"FAIL: control bridge unavailable ({type(exc).__name__}).")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
