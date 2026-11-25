"""Exercise the real Streamlit UI against an isolated temporary database."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
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
    database_path = Path("/tmp") / f"project-continue-browser-{os.getpid()}.sqlite3"
    env = os.environ.copy()
    env.update({
        "APP_ENV": "test",
        "PROJECT_CONTINUE_DB": str(database_path),
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
                try:
                    page = browser.new_page(viewport={"width": 1440, "height": 1000})
                    page.goto(base_url, wait_until="domcontentloaded", timeout=60000)

                    # Wait for Streamlit's client-side app hydration, not merely its shell.
                    page.get_by_role("heading", name="Project Continue").wait_for(timeout=45000)
                    page.get_by_label("Search projects").wait_for(timeout=45000)
                    page.get_by_text("Project registry", exact=True).wait_for(timeout=45000)
                    for heading in (
                        "AI Brain",
                        "Automation Engine",
                        "Memory & Checkpoint Engine",
                        "GitHub integration",
                    ):
                        page.get_by_role("heading", name=heading).wait_for(timeout=45000)

                    # Exercise create -> search -> open -> task create/edit -> reload.
                    suffix = uuid.uuid4().hex[:10]
                    project_name = f"Browser acceptance {suffix}"
                    task_name = f"Acceptance task {suffix}"

                    page.get_by_text("Register a project", exact=False).first.click()
                    page.get_by_label("Project name").fill(project_name)
                    page.get_by_label("Description").fill("Disposable browser acceptance fixture.")
                    page.get_by_role("button", name="Create project").click()
                    page.get_by_text(project_name, exact=True).wait_for(timeout=30000)

                    search = page.get_by_label("Search projects")
                    search.fill(project_name)
                    page.get_by_text(project_name, exact=True).wait_for(timeout=15000)
                    page.get_by_role("button", name="Open details").click()
                    page.get_by_text("Task management", exact=True).wait_for(timeout=15000)

                    page.get_by_text("Create task", exact=False).first.click()
                    page.get_by_label("Task title").fill(task_name)
                    page.get_by_role("group").filter(has_text="Create task").get_by_label("Description").fill("Disposable task used only by CI.")
                    page.get_by_role("button", name="Create task").click()
                    page.get_by_text(task_name, exact=True).wait_for(timeout=20000)

                    page.get_by_text("Edit task", exact=True).first.click()
                    status_control = page.get_by_role("combobox", name="Status").last
                    status_control.click()
                    # Streamlit renders selectbox options in a transient portal;
                    # keyboard selection is more reliable than querying that portal.
                    status_control.press("End")
                    status_control.press("Enter")
                    page.get_by_role("button", name="Save task changes").click()
                    page.get_by_text("Done", exact=True).first.wait_for(timeout=15000)

                    page.reload(wait_until="domcontentloaded", timeout=60000)
                    page.get_by_role("heading", name="Project Continue").wait_for(timeout=45000)
                    page.get_by_label("Search projects").fill(project_name)
                    page.get_by_text(project_name, exact=True).wait_for(timeout=15000)
                    page.get_by_role("button", name="Open details").click()
                    page.get_by_text(task_name, exact=True).wait_for(timeout=15000)

                    # Exercise the mock AI advisory and its explicit approval gate.
                    ai_task_name = f"AI action {suffix}"
                    page.get_by_text("Create task", exact=False).first.click()
                    page.get_by_label("Task title").fill(ai_task_name)
                    page.get_by_role("group").filter(has_text="Create task").get_by_label("Description").fill("Synthetic task for advisory acceptance.")
                    page.get_by_role("button", name="Create task").click()
                    page.get_by_text(ai_task_name, exact=True).wait_for(timeout=20000)
                    page.get_by_role("button", name="Generate next-step suggestion").click()
                    page.get_by_role("button", name="Approve suggestion").wait_for(timeout=20000)
                    page.get_by_role("button", name="Approve suggestion").click()
                    page.get_by_text("Decision recorded: approved", exact=False).wait_for(timeout=15000)

                    # Exercise schedule creation and pause using the allow-listed health check.
                    schedule_name = f"Browser health {suffix}"
                    page.get_by_text("Create scheduled check", exact=True).click()
                    page.get_by_label("Schedule name").fill(schedule_name)
                    page.get_by_role("button", name="Save schedule").click()
                    page.get_by_text(schedule_name, exact=True).wait_for(timeout=15000)
                    page.get_by_role("button", name="Pause").click()
                    page.get_by_role("button", name="Enable").wait_for(timeout=15000)

                    # Exercise project memory, checkpoint preview, session and decision records.
                    memory_key = f"browser-memory-{suffix}"
                    page.get_by_label("Memory key").fill(memory_key)
                    page.get_by_label("Memory value (plain text or JSON)").fill("synthetic acceptance value")
                    page.get_by_role("button", name="Save memory").click()
                    page.get_by_text(memory_key, exact=True).wait_for(timeout=15000)

                    checkpoint_label = f"Browser checkpoint {suffix}"
                    page.get_by_label("Checkpoint label").fill(checkpoint_label)
                    page.get_by_role("button", name="Create verified checkpoint").click()
                    page.get_by_label("Saved checkpoint").wait_for(timeout=15000)
                    page.get_by_role("button", name="Preview recovery").click()
                    page.get_by_text("No missing tasks", exact=False).wait_for(timeout=15000)

                    page.get_by_text("Session history and decisions", exact=True).click()
                    session_summary = f"Browser session {suffix}"
                    page.get_by_label("Session summary").fill(session_summary)
                    page.get_by_role("button", name="Record session").click()
                    decision_title = f"Browser decision {suffix}"
                    decision_title_input = page.get_by_label("Decision title")
                    if not decision_title_input.is_visible():
                        page.get_by_text("Session history and decisions", exact=True).click()
                    decision_title_input.wait_for(state="visible", timeout=15000)
                    decision_title_input.fill(decision_title)
                    page.get_by_role("textbox", name="Context").fill("Synthetic browser acceptance context")
                    page.get_by_role("textbox", name="Decision", exact=True).fill("Keep the isolated workflow")
                    page.get_by_label("Rationale").fill("Verify persistence without touching user data")
                    page.get_by_role("button", name="Record decision").click()
                    decision_row = page.get_by_text(decision_title, exact=True)
                    if not decision_row.is_visible():
                        page.get_by_text("Session history and decisions", exact=True).click()
                    decision_row.wait_for(state="visible", timeout=15000)

                    # Exercise archive -> archived filter -> restore -> active filter.
                    page.get_by_role("button", name="Archive project").click()
                    status_filter = page.get_by_role("combobox", name="Project status")
                    status_filter.click()
                    status_filter.press("End")
                    status_filter.press("Enter")
                    page.get_by_text(project_name, exact=True).wait_for(timeout=15000)
                    page.get_by_role("button", name="Open details").click()
                    page.get_by_role("button", name="Restore project").click()
                    status_filter = page.get_by_role("combobox", name="Project status")
                    status_filter.click()
                    status_filter.press("Home")
                    status_filter.press("Enter")
                    page.get_by_text(project_name, exact=True).wait_for(timeout=15000)

                    # Diagnostics remain read-only and are tested after the CRUD flow.
                    page.get_by_text("Automated self-check", exact=False).first.click()
                    page.get_by_role("button", name="Run self-check").click()
                    page.get_by_text("Overall result", exact=False).wait_for(timeout=30000)
                    result_text = page.locator("body").inner_text()
                    for diagnostic in ("Database connection", "SQLite integrity"):
                        if diagnostic not in result_text:
                            raise AssertionError(f"Self-check did not render {diagnostic!r}.")

                    page.screenshot(path=str(REPORTS / "dashboard-browser-smoke.png"), full_page=True)
                finally:
                    browser.close()
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    print("PASS: Streamlit hydrated, project/task CRUD persisted across reload, and read-only self-check ran.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
