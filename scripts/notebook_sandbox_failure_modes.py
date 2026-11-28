"""Exercise kernel-crash and wall-clock timeout failure modes in the real sandbox."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from scripts.notebook_sandbox import REPOSITORY_ROOT, run_sandbox

FIXTURES = {
    "kernel-crash": "tests/fixtures/notebooks/kernel_crash.ipynb",
    "timeout": "tests/fixtures/notebooks/timeout.ipynb",
}


def _git(*args: str) -> str:
    result = subprocess.run(("git", *args), cwd=REPOSITORY_ROOT, capture_output=True,
        text=True, check=False, timeout=5)
    if result.returncode:
        raise RuntimeError("could not resolve failure fixture Git identity")
    return result.stdout.strip()


def run_failure_modes(output_dir: str | Path) -> dict[str, object]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    commit = _git("rev-parse", "HEAD")
    results: dict[str, object] = {}
    for mode, relative_path in FIXTURES.items():
        blob = _git("rev-parse", "--verify", f"{commit}:{relative_path}")
        request = {"notebook_path": relative_path, "commit_sha": commit, "blob_sha": blob}
        result = run_sandbox(
            REPOSITORY_ROOT / relative_path,
            output,
            request=request,
            checked_out_commit_sha=commit,
            resolved_notebook_path=relative_path,
            resolved_blob_sha=blob,
            timeout_seconds=5 if mode == "timeout" else 120,
        )
        if result.artifact_path is not None or list(output.glob("*.ipynb")):
            raise RuntimeError(f"{mode} failure unexpectedly persisted an artifact")
        if mode == "kernel-crash":
            if result.exit_code == 0 or result.timed_out or "NOTEBOOK_RUNNER_ERROR=" not in result.stderr:
                raise RuntimeError(f"kernel crash was not handled fail-closed: exit={result.exit_code}, stderr={result.stderr!r}")
            results[mode] = {"status": "PASS", "exit_code": result.exit_code}
        else:
            if result.exit_code != 124 or not result.timed_out:
                raise RuntimeError(f"notebook timeout was not enforced: exit={result.exit_code}, timeout={result.timed_out}")
            results[mode] = {"status": "PASS", "exit_code": result.exit_code, "timed_out": True}
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    results = run_failure_modes(args.output_dir)
    print("NOTEBOOK_FAILURE_MODES: PASS")
    print(json.dumps(results, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
