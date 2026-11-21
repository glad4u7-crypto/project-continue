from pathlib import Path
import subprocess
import sys

from scripts.phase06_acceptance import run_acceptance


def test_phase06_file_backed_acceptance_workflow():
    assert run_acceptance() == [
        "task creation, generated IDs, assignment, priority, due date and filters",
        "task update, status transition and assignment clear",
        "dependency creation, completion gate, cycle and cross-project rejection",
        "dependency-aware completion and dependency removal",
        "task activity and audit history",
        "file-backed persistence after close/reopen and SQLite integrity",
        "verified backup contains persisted task records",
    ]


def test_phase06_acceptance_script_runs_from_repository_root():
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/phase06_acceptance.py"],
        cwd=project_root, capture_output=True, text=True, check=True,
    )
    assert "PHASE 06 FILE-BACKED ACCEPTANCE: 7/7 PASS" in result.stdout
