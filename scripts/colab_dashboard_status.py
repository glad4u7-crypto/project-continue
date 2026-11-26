"""Publish a local Colab Streamlit health result as a GitHub commit status.

The health request stays on loopback. A fine-grained GitHub token is read
from Colab Secrets or the process environment and is never printed.
"""
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
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPOSITORY = "glad4u7-crypto/project-continue"
HEALTH_URL = "http://127.0.0.1:8501/_stcore/health"
STATUS_CONTEXT = "project-continue/colab-dashboard-health"
REPO_ROOT = Path(__file__).resolve().parents[1]


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def get_colab_token() -> str:
    """Read the token from an environment variable or Colab's secret store."""
    token = os.environ.get("PROJECT_CONTINUE_GITHUB_STATUS_TOKEN", "").strip()
    if token:
        return token
    try:
        from google.colab import userdata  # type: ignore[import-not-found]
        return str(userdata.get("PROJECT_CONTINUE_GITHUB_STATUS_TOKEN") or "").strip()
    except Exception:
        return ""


def get_checkout_sha() -> str:
    """Return the checked-out repository SHA without exposing command output."""
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    sha = result.stdout.strip()
    if not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
        raise ValueError("Invalid Git checkout SHA")
    return sha.lower()


def check_local_streamlit(timeout: float = 5.0) -> tuple[bool, str]:
    """Check only the local Streamlit health endpoint; never follow redirects."""
    request = Request(HEALTH_URL, headers={"Accept": "text/plain"}, method="GET")
    try:
        with build_opener(_NoRedirectHandler()).open(request, timeout=timeout) as response:
            if response.status == 200:
                return True, "Local Streamlit health endpoint returned HTTP 200"
            return False, f"Local Streamlit health endpoint returned HTTP {response.status}"
    except HTTPError as exc:
        return False, f"Local Streamlit health endpoint returned HTTP {exc.code}"
    except (URLError, TimeoutError, OSError, ValueError):
        return False, "Local Streamlit health endpoint could not be reached"


def publish_commit_status(
    token: str, commit_sha: str, healthy: bool, timeout: float = 10.0
) -> bool:
    """Publish a minimal status on the exact checked-out commit."""
    if not token or not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        return False
    state = "success" if healthy else "failure"
    description = (
        "Colab Streamlit health endpoint returned HTTP 200"
        if healthy else "Colab Streamlit health endpoint check failed"
    )
    payload = json.dumps({
        "state": state,
        "context": STATUS_CONTEXT,
        "description": description,
    }).encode("utf-8")
    request = Request(
        f"https://api.github.com/repos/{REPOSITORY}/statuses/{commit_sha}",
        data=payload,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    try:
        with build_opener(_NoRedirectHandler()).open(request, timeout=timeout) as response:
            return response.status == 201
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return False


def run_once() -> bool:
    token = get_colab_token()
    if not token:
        print("FAIL: Add PROJECT_CONTINUE_GITHUB_STATUS_TOKEN to Colab Secrets.")
        return False
    try:
        commit_sha = get_checkout_sha()
    except (OSError, subprocess.SubprocessError, ValueError):
        print("FAIL: Could not identify the checked-out Git commit.")
        return False

    healthy, detail = check_local_streamlit()
    if not publish_commit_status(token, commit_sha, healthy):
        print("FAIL: Could not publish the dashboard status to GitHub.")
        return False
    print(f"{'PASS' if healthy else 'FAIL'}: {detail}; GitHub status published for {commit_sha}")
    return healthy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=0,
        help="Repeat while this process runs (minimum 300 seconds); 0 means one check.",
    )
    args = parser.parse_args(argv)
    if args.interval_seconds and not 300 <= args.interval_seconds <= 86400:
        print("FAIL: interval must be 300–86400 seconds, or 0 for one check.")
        return 2
    if args.interval_seconds == 0:
        return 0 if run_once() else 1
    try:
        while True:
            run_once()
            time.sleep(args.interval_seconds)
    except KeyboardInterrupt:
        print("Stopped the health reporter; the Streamlit dashboard was not stopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
