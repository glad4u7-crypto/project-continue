"""CI-only harmless notebook end-to-end sandbox acceptance."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from scripts.phase20_notebook_sandbox import execute_notebook_sandbox


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    fixture = repo / "tests/fixtures/phase20_safe_notebook.ipynb"
    digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
    approval_id = "phase20-ci-harmless-fixture"
    policy_data = {
        "schema_version": 1,
        "entries": [{
            "path": fixture.name, "sha256": digest, "approval_id": approval_id,
            "enabled": True, "network_access": False, "secrets_access": False,
            "external_mounts": False,
        }],
    }
    with tempfile.TemporaryDirectory(prefix="phase20-notebook-policy-") as tmp:
        policy = Path(tmp) / "allow.json"
        policy.write_text(json.dumps(policy_data), encoding="utf-8")
        result = execute_notebook_sandbox(
            fixture.parent, fixture.name, current_commit=args.commit,
            requested_commit=args.commit, approval_id=approval_id,
            policy_path=policy, image_id=args.image_id, timeout_seconds=15,
        )
    output = fixture.parent / "phase20_safe_notebook.executed.ipynb"
    try:
        document = json.loads(output.read_text(encoding="utf-8"))
        texts = []
        for cell in document["cells"]:
            for item in cell.get("outputs", []):
                texts.extend(item.get("text", []) if isinstance(item.get("text"), list)
                             else [item.get("text", "")])
        combined = "".join(texts)
        assert "phase20-notebook-ok" in combined
        assert "network-denied" in combined
        assert result["network_access"] is False
        assert result["secrets_access"] is False
        assert result["external_mounts"] is False
        assert all(cell.get("execution_count") is not None
                   for cell in document["cells"] if cell["cell_type"] == "code")
        print(json.dumps({"status": "PASS", "result": result,
                          "network_probe": "DENIED", "secret_probe": "NO_GITHUB_TOKEN",
                          "artifact_readback": "VALID"} , sort_keys=True))
    finally:
        try:
            output.unlink()
        except FileNotFoundError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
