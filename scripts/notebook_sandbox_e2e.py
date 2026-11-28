"""Run the allow-listed harmless notebook fixture inside the real Docker sandbox."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from scripts.notebook_sandbox import REPOSITORY_ROOT, run_sandbox

FIXTURE_PATH = "tests/fixtures/notebooks/harmless_execution.ipynb"


def _git_output(*args: str) -> str:
    result = subprocess.run(
        ("git", *args), cwd=REPOSITORY_ROOT, capture_output=True,
        text=True, check=False, timeout=5,
    )
    if result.returncode != 0:
        raise RuntimeError("could not resolve fixture identity from Git")
    return result.stdout.strip()


def run_acceptance(output_dir: str | Path) -> dict[str, object]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    commit_sha = _git_output("rev-parse", "HEAD")
    blob_sha = _git_output("rev-parse", "--verify", f"{commit_sha}:{FIXTURE_PATH}")
    request = {
        "notebook_path": FIXTURE_PATH,
        "commit_sha": commit_sha,
        "blob_sha": blob_sha,
    }
    result = run_sandbox(
        REPOSITORY_ROOT / FIXTURE_PATH,
        output,
        request=request,
        checked_out_commit_sha=commit_sha,
        resolved_notebook_path=FIXTURE_PATH,
        resolved_blob_sha=blob_sha,
    )
    if result.exit_code != 0 or result.timed_out or result.execution_status != "completed" or not result.artifact_path:
        raise RuntimeError(f"harmless notebook sandbox failed: exit={result.exit_code}, timeout={result.timed_out}, status={result.execution_status}")
    artifact = Path(result.artifact_path)
    document = json.loads(artifact.read_text(encoding="utf-8"))
    code_cells = [cell for cell in document["cells"] if cell["cell_type"] == "code"]
    if [cell["execution_count"] for cell in code_cells] != [1, 2]:
        raise RuntimeError("notebook execution counts did not persist as expected")
    output_text = "\n".join(
        str(output_item.get("text", ""))
        for cell in code_cells
        for output_item in cell.get("outputs", [])
        if output_item.get("output_type") == "stream"
    )
    if "SANDBOX_E2E_OK 42" not in output_text or "SECOND_CELL_OK 42" not in output_text:
        raise RuntimeError("notebook cell output did not persist as expected")
    if any(output_item.get("output_type") == "error" for cell in code_cells for output_item in cell.get("outputs", [])):
        raise RuntimeError("harmless notebook unexpectedly contains a cell error")
    payload = artifact.read_bytes()
    return {
        "status": "PASS",
        "commit_sha": commit_sha,
        "notebook_blob_sha": blob_sha,
        "executed_code_cells": len(code_cells),
        "artifact_bytes": len(payload),
        "artifact_sha256": hashlib.sha256(payload).hexdigest(),
        "artifact_path": str(artifact),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    summary = run_acceptance(args.output_dir)
    print("NOTEBOOK_E2E: PASS")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
