from pathlib import Path
import subprocess
import sys

from scripts.phase05_acceptance import run_acceptance


def test_phase05_file_backed_acceptance_workflow():
    assert run_acceptance() == [
        "project registration and persistence",
        "task-derived progress and status breakdown",
        "metadata update and activity history",
        "archive, filtering, and restore",
        "reopen persistence and SQLite integrity_check",
    ]


def test_phase05_acceptance_script_runs_from_repository_root():
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/phase05_acceptance.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "PHASE 05 FILE-BACKED ACCEPTANCE: 5/5 PASS" in result.stdout
