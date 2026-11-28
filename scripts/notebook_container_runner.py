"""Execute one already-authorized notebook inside the isolated Docker image."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from scripts.notebook_read import read_notebook_redacted
from scripts.notebook_validation import MAX_NOTEBOOK_BYTES


def summarize_notebook(document: dict[str, Any], status: str, artifact_bytes: int, artifact_sha256: str) -> dict[str, Any]:
    code_cells = [cell for cell in document.get("cells", []) if cell.get("cell_type") == "code"]
    return {
        "status": status,
        "executed_code_cells": sum(cell.get("execution_count") is not None for cell in code_cells),
        "error_cells": sum(
            any(output.get("output_type") == "error" for output in cell.get("outputs", []))
            for cell in code_cells
        ),
        "artifact_name": "executed.ipynb",
        "artifact_bytes": artifact_bytes,
        "artifact_sha256": artifact_sha256,
    }


def write_artifact_exclusive(path: str | Path, payload: bytes, *, output_root: str | Path = "/workspace/output") -> None:
    if not isinstance(payload, bytes) or len(payload) > MAX_NOTEBOOK_BYTES:
        raise ValueError("notebook artifact exceeds the 64 KiB limit")
    destination = Path(path)
    if destination.name != "executed.ipynb" or destination.parent != Path(output_root):
        raise ValueError("artifact path is not the fixed sandbox output path")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(destination, flags, 0o644)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def execute_notebook(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    if Path(input_path) != Path("/workspace/input.ipynb"):
        raise ValueError("input path is not the fixed read-only sandbox mount")
    if Path(output_path) != Path("/workspace/output/executed.ipynb"):
        raise ValueError("output path is not the fixed sandbox artifact path")
    raw = Path(input_path).read_bytes()
    valid, document, _ = read_notebook_redacted(raw)
    if not valid or document is None:
        raise ValueError("notebook failed structural validation")
    import nbformat
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError

    notebook = nbformat.from_dict(document)
    status = "completed"
    try:
        NotebookClient(
            notebook, timeout=60, kernel_name="python3", allow_errors=False,
            resources={"metadata": {"path": "/workspace"}},
        ).execute()
    except CellExecutionError:
        status = "cell_error"

    serialized = nbformat.writes(notebook).encode("utf-8")
    output_valid, sanitized, _ = read_notebook_redacted(serialized)
    if not output_valid or sanitized is None:
        raise ValueError("executed notebook failed bounded validation")
    payload = json.dumps(sanitized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    write_artifact_exclusive(output_path, payload)
    return summarize_notebook(sanitized, status, len(payload), hashlib.sha256(payload).hexdigest())


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print("NOTEBOOK_RUNNER_ERROR=invalid_arguments", file=sys.stderr)
        return 2
    try:
        summary = execute_notebook(args[0], args[1])
    except Exception as exc:
        frames = traceback.extract_tb(exc.__traceback__)[-5:]
        trace = ";".join(f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}" for frame in frames)
        attribute = getattr(exc, "name", None) if isinstance(exc, AttributeError) else None
        target_type = type(getattr(exc, "obj", None)).__name__ if isinstance(exc, AttributeError) else None
        print(f"NOTEBOOK_RUNNER_ERROR={type(exc).__name__};ATTRIBUTE={attribute};TARGET_TYPE={target_type};TRACE={trace}", file=sys.stderr)
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
