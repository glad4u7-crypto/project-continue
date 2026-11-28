"""Real Chromium acceptance for an isolated Streamlit app instance."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
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
        "INITIAL_ADMIN_PASSWORD", "PROJECT_CONTINUE_POSTGRES_DSN",
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


def browser_round_trip(base_url: str, *, expect_existing: bool) -> None:
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
            if expect_existing:
                page.get_by_text("Browser acceptance project", exact=True).wait_for(timeout=15000)
                page.get_by_role("button", name="Open details").click()
                page.get_by_text("Browser acceptance task", exact=True).wait_for(timeout=15000)
                return

            page.get_by_role("button", name="Register a project").click()
            page.get_by_label("Project name").fill("Browser acceptance project")
            page.get_by_label("Description").fill("Created by isolated Chromium acceptance")
            page.get_by_role("button", name="Create project").click()
            page.get_by_text("Browser acceptance project", exact=True).wait_for(timeout=15000)

            page.get_by_role("button", name="Open details").click()
            page.get_by_role("button", name="Create task").first.click()
            page.get_by_label("Task title").fill("Browser acceptance task")
            page.get_by_label("Description").last.fill("Persist across app restart")
            page.get_by_role("button", name="Create task").click()
            page.get_by_text("Browser acceptance task", exact=True).wait_for(timeout=15000)

            page.get_by_role("button", name="Mark complete").click()
            page.get_by_text("Done", exact=True).first.wait_for(timeout=15000)
            if page_errors:
                raise AssertionError(f"Browser page errors: {page_errors}")
        except PlaywrightTimeoutError as exc:
            raise AssertionError(f"Browser UI action timed out: {exc}") from exc
        finally:
            browser.close()


def browser_login_round_trip(base_url: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            response = page.goto(base_url, wait_until="domcontentloaded", timeout=30000)
            if response is None or response.status != 200:
                raise AssertionError("Production login page did not return HTTP 200")
            page.get_by_text("Project Continue — Sign in", exact=True).wait_for(timeout=20000)
            if page.get_by_text("Project registry", exact=True).count():
                raise AssertionError("Production dashboard rendered before authentication")
            page.get_by_label("Email").fill("browser-admin@example.invalid")
            page.get_by_label("Password").fill("Browser-Test-Only-Password-123!")
            page.get_by_role("button", name="Sign in").click()
            page.get_by_text("Authenticated production operator", exact=True).wait_for(timeout=20000)
            page.get_by_text("Project registry", exact=True).wait_for(timeout=15000)
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

        first = start_app(database_path, log_path, port)
        try:
            wait_for_health(health_url, first, log_path)
            browser_round_trip(base_url, expect_existing=False)
        finally:
            stop_app(first)

        second = start_app(database_path, log_path, port)
        try:
            wait_for_health(health_url, second, log_path)
            browser_round_trip(base_url, expect_existing=True)
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
            browser_login_round_trip(production_url)
        finally:
            stop_app(production)
        if production.poll() is None:
            raise AssertionError("Production-auth test process was not stopped")

        print("PHASE20_STREAMLIT_BROWSER_ACCEPTANCE=PASS")
        print("health_endpoint=HTTP_200")
        print("browser=Chromium")
        print("project_create=PASS")
        print("task_create_and_complete=PASS")
        print("restart_persistence=PASS")
        print("production_login_gate=PASS")
        print("isolated_process_cleanup=PASS")
        print("external_credentials=NOT_INJECTED")
        print("live_database_or_service=NOT_TOUCHED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
