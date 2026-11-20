"""Repository secret-hygiene regression checks."""

from pathlib import Path
import subprocess

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.production",
        ".streamlit/secrets.toml",
        ".data/project_continue.sqlite3",
        "private.pem",
        "private.key",
        "logs/application.log",
    ],
)
def test_sensitive_local_files_are_git_ignored(path):
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", path],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0, f"{path} is not ignored by Git"


def test_environment_template_is_not_ignored():
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", ".env.example"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 1, ".env.example must remain trackable"


def test_environment_template_contains_no_active_github_token():
    template = (ROOT / ".env.example").read_text(encoding="utf-8")
    active_assignments = [
        line for line in template.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
        and line.split("=", 1)[0].strip() == "GITHUB_TOKEN"
    ]
    assert active_assignments == []
