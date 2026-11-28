"""Commit-bound notebook execution in a disposable, networkless Docker sandbox."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from scripts.phase20_notebook_policy import authorize_notebook
from scripts.phase20_notebooks import MAX_NOTEBOOK_BYTES, read_notebook, validate_notebook_document

_IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
_MAX_TIMEOUT = 120


class NotebookExecutionError(RuntimeError):
    pass


def execute_notebook_sandbox(
    notebook_root: str | Path,
    notebook_name: str,
    *,
    current_commit: str,
    requested_commit: str,
    approval_id: str,
    policy_path: str | Path,
    image_id: str,
    timeout_seconds: int = 30,
    docker_bin: str = "docker",
) -> dict:
    if not _IMAGE_ID.fullmatch(image_id or ""):
        raise PermissionError("sandbox image must be pinned by immutable image ID")
    if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or not 1 <= timeout_seconds <= _MAX_TIMEOUT:
        raise ValueError("execution timeout must be between 1 and 120 seconds")
    repo_root = Path(__file__).resolve().parents[1]
    verified_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root,
        capture_output=True, text=True, timeout=10, check=False,
    )
    if verified_commit.returncode != 0 or verified_commit.stdout.strip() != current_commit:
        raise PermissionError("current repository commit could not be verified")
    authorization = authorize_notebook(
        notebook_root, notebook_name, current_commit=current_commit,
        requested_commit=requested_commit, approval_id=approval_id,
        policy_path=policy_path,
    )
    root = Path(notebook_root).resolve(strict=True)
    source = root / authorization["path"]
    if source.stat().st_size > MAX_NOTEBOOK_BYTES:
        raise PermissionError("notebook exceeds execution size limit")
    source_document = read_notebook(root, notebook_name)["notebook"]
    validate_notebook_document(source_document)
    output_name = source.stem + ".executed.ipynb"
    output_target = root / output_name
    if output_target.exists() or output_target.is_symlink():
        raise FileExistsError("execution artifact already exists; refusing overwrite")
    container_name = "pc-nb-" + uuid.uuid4().hex[:16]
    with tempfile.TemporaryDirectory(prefix="pc-notebook-") as temp:
        staged_input = Path(temp) / "input.ipynb"
        staged_input.write_text(json.dumps(source_document, ensure_ascii=False), encoding="utf-8")
        staged_input.chmod(0o444)
        Path(temp).chmod(0o755)
        # The only bind mount is a sanitized, read-only notebook. Output and /tmp
        # are bounded tmpfs mounts. No host environment variables are forwarded.
        create = [
            docker_bin, "create", "--name", container_name,
            "--network", "none", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--pids-limit", "64",
            "--memory", "512m", "--cpus", "1",
            "--user", "65534:65534",
            "--tmpfs", "/tmp:rw,nosuid,nodev,noexec,size=64m,uid=65534,gid=65534",
            "--tmpfs", "/output:rw,nosuid,nodev,noexec,size=16m,uid=65534,gid=65534",
            "-v", f"{staged_input}:/input/notebook.ipynb:ro",
            image_id, "/input/notebook.ipynb", "/output/executed.ipynb",
            "--timeout", str(timeout_seconds),
        ]
        try:
            made = subprocess.run(create, capture_output=True, text=True, timeout=20, check=False)
            if made.returncode != 0:
                raise NotebookExecutionError("sandbox container creation failed")
            started = subprocess.run(
                [docker_bin, "start", "--attach", container_name],
                capture_output=True, text=True, timeout=timeout_seconds + 20, check=False,
            )
            execution_failed = started.returncode != 0
            staged_output = Path(temp) / "executed.ipynb"
            copied = subprocess.run(
                [docker_bin, "cp", f"{container_name}:/output/executed.ipynb", str(staged_output)],
                capture_output=True, text=True, timeout=20, check=False,
            )
            if copied.returncode != 0 or not staged_output.is_file():
                raise NotebookExecutionError("sandbox output artifact is unavailable")
            if staged_output.stat().st_size > MAX_NOTEBOOK_BYTES:
                raise NotebookExecutionError("sandbox output artifact exceeds size limit")
            executed_doc = json.loads(staged_output.read_text(encoding="utf-8"))
            validate_notebook_document(executed_doc)
            # Recursively sanitize secrets before persisting the artifact.
            from scripts.phase20_notebooks import _redact_tree
            safe_doc = _redact_tree(executed_doc)
            payload = (json.dumps(safe_doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(output_target, flags, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            result = {
                "status": "FAIL" if execution_failed else "PASS",
                "path": output_name, "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "commit_sha": current_commit, "approval_id": approval_id,
                "network_access": False, "secrets_access": False,
                "external_mounts": False, "container_image_id": image_id,
            }
            if execution_failed:
                raise NotebookExecutionError(
                    "notebook execution failed; sanitized traceback artifact saved as " + output_name
                )
            return result
        except subprocess.TimeoutExpired as exc:
            raise NotebookExecutionError("sandbox execution timed out") from exc
        finally:
            try:
                subprocess.run([docker_bin, "rm", "-f", container_name],
                               capture_output=True, text=True, timeout=20, check=False)
            except (OSError, subprocess.TimeoutExpired):
                pass
