import os
import subprocess
import sys
from pathlib import Path

from app.main import main


def test_main_returns_success():
    assert main() == 0


def test_python_module_entrypoint_starts_successfully():
    project_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["APP_NAME"] = "Project Continue Test"
    env["APP_ENV"] = "test"

    result = subprocess.run(
        [sys.executable, "-m", "app"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == (
        "Project Continue Test core entry point ready [test]"
    )
