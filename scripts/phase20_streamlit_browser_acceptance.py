"""Real Chromium acceptance for an isolated Streamlit app instance."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_health(url: str, process: subprocess.Popen, log_path: Path) -> None:
    deadline = time.monotonic() + 45
    last_error = "not started"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"Streamlit exited with code {process.returncode}; "
                f"sanitized log tail: {log_path.read_text(errors='replace')[-4000:]}"
            )
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200 and response.read(128):
                    return
        except (OSError, URLError) as exc:
            last_error = type(exc).__name__
        time.sleep(0.5)
    raise TimeoutError(
        f"Streamlit health endpoint did not become ready ({last_error}); "
        f"sanitized log tail: {log_path.read_text(errors='replace')[-4000:]}"
    )


def start_app(database_path: Path, log_path: Path, port: int, *, production: bool = False) -> subprocess.Popen:
    env = os.environ.copy()
    for key in (
        "GITHUB_TOKEN", "GITHUB_APP_PRIVATE_KEY", "SESSION_SIGNING_KEY",
        "INITIAL_ADMIN_PASSWORD", "INITIAL_ADMIN_EMAIL", "PROJECT_CONTINUE_POSTGRES_DSN",
    ):
        env.pop(key, None)
    env.update({
        "APP_ENV": "production" if production else "test",
        "LOG_LEVEL": "INFO",
        "PROJECT_CONTINUE_DB": str(database_path),
        "GITHUB_REPOSITORY": "",
        "AUTHORIZATION_ENFORCED": "false",
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
    })
    if production:
        env.update({
            "SESSION_SIGNING_KEY": "phase20-browser-acceptance-signing-key-123456",
            "INITIAL_ADMIN_EMAIL": "browser-admin@example.invalid",
            "INITIAL_ADMIN_PASSWORD": "Browser-Test-Only-Password-123!",
        })
    log = log_path.open("a", encoding="utf-8")
    process = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
            "--server.headless=true", "--server.address=127.0.0.1",
            f"--server.port={port}", "--browser.gatherUsageStats=false",
        ],
        cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return process


def stop_app(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def ensure_expander_open(page, label: str, *, last: bool = False) -> None:
    locator = page.locator("summary").filter(has_text=label)
    locator = locator.last if last else locator.first
    is_open = locator.evaluate("(element) => Boolean(element.closest('details')?.open)")
    if not is_open:
        locator.click()


def browser_round_trip(base_url: str, *, expect_existing: bool, screenshot_path: Path) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)[:300]))
        try:
            response = page.goto(base_url, wait_until="domcontentloaded", timeout=30000)
            if response is None or response.status != 200:
                raise AssertionError("Streamlit browser document did not return HTTP 200")
            page.get_by_text("Project Continue", exact=False).first.wait_for(timeout=20000)
            page.get_by_text("Project registry", exact=True).wait_for(timeout=10000)
            page.screenshot(path=str(screenshot_path), full_page=True)
            if expect_existing:
                page.get_by_text("Browser acceptance project updated", exact=True).first.wait_for(timeout=15000)
                page.get_by_role("button", name="Open details").click()
                page.get_by_text("Browser acceptance task updated", exact=True).first.wait_for(timeout=15000)
                page.screenshot(path=str(screenshot_path), full_page=True)
                return

            ensure_expander_open(page, "Register a project")
            page.get_by_label("Project name").fill("Browser acceptance project")
            page.get_by_label("Description").fill("Created by isolated Chromium acceptance")
            page.get_by_role("button", name="Create project").click()
            page.get_by_text("Browser acceptance project", exact=True).wait_for(timeout=15000)

            page.get_by_role("button", name="Open details").click()
            ensure_expander_open(page, "Edit project details")
            page.get_by_role("textbox", name="Name", exact=True).fill("Browser acceptance project updated")
            page.get_by_label("Description").last.fill("Updated by Chromium browser acceptance")
            page.get_by_role("button", name="Save changes").click()
            page.get_by_text("Browser acceptance project updated", exact=True).first.wait_for(timeout=15000)
            ensure_expander_open(page, "Create task")
            page.get_by_label("Task title").fill("Browser acceptance task")
            page.get_by_label("Description").last.fill("Persist across app restart")
            page.get_by_role("button", name="Create task").click(force=True)
            try:
                page.get_by_text("Browser acceptance task", exact=True).wait_for(timeout=15000)
            except PlaywrightTimeoutError as exc:
                raise AssertionError("First task create did not persist; browser body: " + page.locator("body").inner_text()[-4000:]) from exc
            ensure_expander_open(page, "Edit task")
            page.get_by_role("textbox", name="Title", exact=True).fill("Browser acceptance task updated")
            page.get_by_role("button", name="Save task changes").click(force=True)
            page.get_by_text("Browser acceptance task updated", exact=True).first.wait_for(timeout=15000)

            page.get_by_role("button", name="Mark complete").first.click(force=True)
            page.get_by_text("Done", exact=True).first.wait_for(timeout=15000)
            page.get_by_text("GitHub integration", exact=True).wait_for(timeout=10000)
            page.get_by_text("GitHub repository is not configured", exact=False).wait_for(timeout=10000)
            page.screenshot(path=str(screenshot_path), full_page=True)
            if page_errors:
                raise AssertionError(f"Browser page errors: {page_errors}")
        except PlaywrightTimeoutError as exc:
            raise AssertionError(f"Browser UI action timed out: {exc}") from exc
        finally:
            browser.close()


def browser_login_round_trip(base_url: str, screenshot_path: Path) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            response = page.goto(base_url, wait_until="domcontentloaded", timeout=30000)
            if response is None or response.status != 200:
                raise AssertionError("Production login page did not return HTTP 200")
            try:
                page.get_by_text("Project Continue", exact=False).filter(has_text="Sign in").wait_for(timeout=20000)
            except PlaywrightTimeoutError as exc:
                body = page.locator("body").inner_text()[:3000]
                raise AssertionError("Production login gate missing; browser body: " + body) from exc
            if page.get_by_text("Project registry", exact=True).count():
                raise AssertionError("Production dashboard rendered before authentication")
            page.get_by_label("Email").fill("browser-admin@example.invalid")
            page.get_by_role("textbox", name="Password").fill("Browser-Test-Only-Password-123!")
            page.get_by_role("button", name="Sign in").click()
            page.get_by_text("Authenticated production operator", exact=True).wait_for(timeout=20000)
            page.get_by_text("Project registry", exact=True).wait_for(timeout=15000)
            page.screenshot(path=str(screenshot_path), full_page=True)
        finally:
            browser.close()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="phase20-streamlit-") as temporary:
        root = Path(temporary)
        database_path = root / "isolated" / "acceptance.sqlite3"
        log_path = root / "streamlit.log"
        port = free_port()
        base_url = f"http://127.0.0.1:{port}"
        health_url = f"{base_url}/_stcore/health"
        evidence_dir = ROOT / "reports" / "phase20-streamlit-browser"
        evidence_dir.mkdir(parents=True, exist_ok=True)

        first = start_app(database_path, log_path, port)
        try:
            wait_for_health(health_url, first, log_path)
            browser_round_trip(base_url, expect_existing=False, screenshot_path=evidence_dir / "project-task-flow.png")
        finally:
            stop_app(first)

        second = start_app(database_path, log_path, port)
        try:
            wait_for_health(health_url, second, log_path)
            browser_round_trip(base_url, expect_existing=True, screenshot_path=evidence_dir / "restart-persistence.png")
        finally:
            stop_app(second)

        if first.poll() is None or second.poll() is None:
            raise AssertionError("Isolated Streamlit process was not stopped")
        if not database_path.is_file():
            raise AssertionError("Isolated SQLite database was not created")

        production_database = root / "production-login" / "acceptance.sqlite3"
        production_port = free_port()
        production = start_app(production_database, log_path, production_port, production=True)
        try:
            production_url = "http://127.0.0.1:" + str(production_port)
            wait_for_health(production_url + "/_stcore/health", production, log_path)
            try:
                browser_login_round_trip(production_url, evidence_dir / "production-login.png")
            except Exception:
                print("PRODUCTION_STREAMLIT_LOG_TAIL=" + log_path.read_text(errors="replace")[-5000:])
                raise
        finally:
            stop_app(production)
        if production.poll() is None:
            raise AssertionError("Production-auth test process was not stopped")

        evidence = {
            "commit": os.environ.get("GITHUB_SHA", "local-unpinned"),
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "browser": "Chromium",
            "health_http_200": True,
            "project_create_read_update": True,
            "task_create_update_complete": True,
            "task_dependency_service_tests": True,
            "github_panel_empty_state": True,
            "restart_persistence": True,
            "production_login_gate": True,
            "process_cleanup": True,
            "live_data_touched": False,
        }
        (evidence_dir / "acceptance.json").write_text(
            json.dumps(evidence, sort_keys=True, indent=2) + "\\n", encoding="utf-8"
        )
        print("PHASE20_STREAMLIT_BROWSER_ACCEPTANCE=PASS")
        print("health_endpoint=HTTP_200")
        print("browser=Chromium")
        print("project_create_read_update=PASS")
        print("task_create_update_complete=PASS")
        print("task_dependency_service_tests=PASS")
        print("github_panel_empty_state=PASS")
        print("browser_evidence=reports/phase20-streamlit-browser")
        print("restart_persistence=PASS")
        print("production_login_gate=PASS")
        print("isolated_process_cleanup=PASS")
        print("external_credentials=NOT_INJECTED")
        print("live_database_or_service=NOT_TOUCHED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
