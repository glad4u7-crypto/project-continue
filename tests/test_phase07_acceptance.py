from pathlib import Path
import subprocess
import sys


def test_phase07_isolated_runtime_acceptance_script():
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/phase07_acceptance.py"],
        cwd=project_root, capture_output=True, text=True, check=True,
    )
    assert "[PASS] Task ranking" in result.stdout
    assert "[PASS] Explainable priority calculation" in result.stdout
    assert "[PASS] Direct/transitive dependency analysis" in result.stdout
    assert "[PASS] Next actionable task selection" in result.stdout
    assert "[PASS] Blocked task detection" in result.stdout
    assert "[PASS] Start/continue/unblock recommendations" in result.stdout
    assert "[PASS] Dependency-aware completion verification" in result.stdout
    assert "PHASE 07 RUNTIME ACCEPTANCE: PASS" in result.stdout
