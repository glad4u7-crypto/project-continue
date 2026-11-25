"""Launch the real Streamlit app and exercise its read-only browser smoke path."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_streamlit(url: str, process: subprocess.Popen[str], log_path: Path) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Streamlit exited early; inspect {log_path}")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(1)
    raise TimeoutError(f"Streamlit did not become healthy; inspect {log_path}")


def main() -> int:
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    log_path = REPORTS / "streamlit-browser-smoke.log"
    env = os.environ.copy()
    env.update({
        "APP_ENV": "test",
        "PROJECT_CONTINUE_DB": str(Path("/tmp") / f"project-continue-browser-{os.getpid()}.sqlite3"),
        "GITHUB_REPOSITORY": "glad4u7-crypto/project-continue",
        "PYTHONUNBUFFERED": "1",
    })

    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                sys.executable, "-m", "streamlit", "run", "app.py",
                "--server.headless=true",
                f"--server.port={port}",
                "--server.address=127.0.0.1",
                "--browser.gatherUsageStats=false",
            ],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            wait_for_streamlit(f"{base_url}/_stcore/health", process, log_path)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
                page.get_by_text("Project Continue", exact=False).first.wait_for(timeout=30000)

                body = page.locator("body").inner_text()
                expected = [
                    "Register a project",
                    "Search projects",
                    "AI Brain",
                    "Automation Engine",
                    "Notifications",
                    "Memory & Checkpoint Engine",
                    "GitHub integration",
                ]
                missing = [label for label in expected if label not in body]
                if missing:
                    raise AssertionError(f"Dashboard sections missing: {missing}")

                # This is intentionally the only interaction: the diagnostics are read-only.
                page.get_by_text("Automated self-check", exact=False).first.click()
                page.get_by_role("button", name="Run self-check").click()
                page.get_by_text("Overall result", exact=False).wait_for(timeout=30000)
                result_text = page.locator("body").inner_text()
                for diagnostic in ("Database connection", "SQLite integrity"):
                    if diagnostic not in result_text:
                        raise AssertionError(f"Self-check did not render {diagnostic!r}.")

                page.screenshot(path=str(REPORTS / "dashboard-browser-smoke.png"), full_page=True)
                browser.close()
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    print("PASS: Streamlit launched, dashboard sections rendered, read-only self-check executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
