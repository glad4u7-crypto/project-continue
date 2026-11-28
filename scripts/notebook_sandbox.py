"""Build and supervise a constrained, identity-bound Docker notebook runner."""
from __future__ import annotations
import base64
import hashlib
import json
import os
import re
import resource
import signal
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from scripts.notebook_execution_policy import authorize_notebook_execution
from scripts.notebook_read import read_notebook_redacted

SANDBOX_IMAGE = "project-continue-notebook-sandbox:ci"
SANDBOX_UID = 10001
EXECUTION_TIMEOUT_SECONDS = 120
MAX_OUTPUT_BYTES = 128 * 1024
MAX_NOTEBOOK_BYTES = 64 * 1024
_CONTAINER_NAME_RE = re.compile(r"^pc-notebook-[0-9a-f]{32}$")
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SandboxResult:
    exit_code: int
    timed_out: bool
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    artifact_path: str | None = None
    execution_status: str | None = None


def git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def _load_trusted_blob(
    notebook_path: str | Path,
    *,
    checked_out_commit_sha: str,
    resolved_notebook_path: str,
    resolved_blob_sha: str,
) -> bytes:
    candidate = Path(notebook_path)
    if candidate.is_symlink():
        raise ValueError("notebook path must not be a symlink")
    if candidate.resolve(strict=True) != (REPOSITORY_ROOT / resolved_notebook_path).resolve(strict=True):
        raise ValueError("local notebook path does not match the authorized repository path")
    head = subprocess.run(
        ("git", "rev-parse", "HEAD"), cwd=REPOSITORY_ROOT,
        capture_output=True, text=True, check=False, timeout=5,
    )
    if head.returncode != 0 or head.stdout.strip() != checked_out_commit_sha:
        raise ValueError("working checkout does not match the trusted commit SHA")
    tree_blob = subprocess.run(
        ("git", "rev-parse", "--verify", f"{checked_out_commit_sha}:{resolved_notebook_path}"),
        cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=False, timeout=5,
    )
    if tree_blob.returncode != 0 or tree_blob.stdout.strip() != resolved_blob_sha:
        raise ValueError("trusted commit tree does not contain the authorized notebook blob")
    blob = subprocess.run(
        ("git", "cat-file", "blob", resolved_blob_sha), cwd=REPOSITORY_ROOT,
        capture_output=True, text=False, check=False, timeout=5,
    )
    if blob.returncode != 0 or git_blob_sha1(blob.stdout) != resolved_blob_sha:
        raise ValueError("could not read the exact authorized Git blob")
    return blob.stdout


def _mount_path(path: Path) -> str:
    value = str(path)
    if any(character in value for character in (",", "\n", "\r")):
        raise ValueError("sandbox mount path contains unsupported characters")
    return value


def build_sandbox_command(notebook_path: str | Path, *, container_name: str | None = None) -> tuple[str, ...]:
    """Return fixed Docker argv; the only host bind mount is the read-only notebook."""
    raw_notebook = Path(notebook_path)
    if raw_notebook.is_symlink():
        raise ValueError("sandbox notebook path must not be a symlink")
    notebook = raw_notebook.resolve(strict=True)
    if not notebook.is_file() or notebook.suffix.lower() != ".ipynb":
        raise ValueError("notebook input must be a regular .ipynb file")
    name = container_name or f"pc-notebook-{uuid.uuid4().hex}"
    if not isinstance(name, str) or not _CONTAINER_NAME_RE.fullmatch(name):
        raise ValueError("sandbox container name is invalid")
    return (
        "docker", "run", "--rm", "--name", name, "--network=none", "--stop-timeout=5",
        "--user", f"{SANDBOX_UID}:{SANDBOX_UID}", "--read-only", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--pids-limit=64", "--memory=512m", "--cpus=1",
        "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=64m",
        "--tmpfs", "/workspace/output:rw,noexec,nosuid,nodev,size=1m,uid=10001,gid=10001,mode=700",
        "--mount", f"type=bind,src={_mount_path(notebook)},dst=/workspace/input.ipynb,readonly",
        "--workdir", "/workspace", SANDBOX_IMAGE,
        "python", "-m", "scripts.notebook_container_runner",
        "/workspace/input.ipynb", "/workspace/output/executed.ipynb",
    )


def _apply_output_limits() -> None:
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES + 1, MAX_OUTPUT_BYTES + 1))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _read_bounded(stream) -> tuple[str, bool]:
    stream.seek(0)
    data = stream.read(MAX_OUTPUT_BYTES + 1)
    return data[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"), len(data) > MAX_OUTPUT_BYTES


def _cleanup_container(container_name: str) -> None:
    for command in (("docker", "kill", container_name), ("docker", "rm", "--force", container_name)):
        try:
            subprocess.run(command, shell=False, check=False, capture_output=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass


def _write_exclusive(path: Path, payload: bytes, *, mode: int = 0o600) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def run_sandbox(
    notebook_path: str | Path,
    output_dir: str | Path,
    *,
    request: object,
    checked_out_commit_sha: str,
    resolved_notebook_path: str,
    resolved_blob_sha: str,
    timeout_seconds: int = EXECUTION_TIMEOUT_SECONDS,
) -> SandboxResult:
    """Authorize, execute in Docker, then persist only a validated/redacted artifact."""
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= EXECUTION_TIMEOUT_SECONDS:
        raise ValueError("sandbox timeout must be between 1 and 120 seconds")
    raw_notebook, raw_output = Path(notebook_path), Path(output_dir)
    if raw_notebook.is_symlink() or raw_output.is_symlink():
        return SandboxResult(3, False, "", "sandbox paths must not be symlinks", False, False)
    try:
        notebook, destination = raw_notebook.resolve(strict=True), raw_output.resolve(strict=True)
        if not notebook.is_file() or notebook.suffix.lower() != ".ipynb" or not destination.is_dir():
            return SandboxResult(3, False, "", "invalid notebook or output path", False, False)
    except OSError:
        return SandboxResult(3, False, "", "notebook or output path is unavailable", False, False)
    authorized, _ = authorize_notebook_execution(
        request, checked_out_commit_sha=checked_out_commit_sha,
        resolved_notebook_path=resolved_notebook_path, resolved_blob_sha=resolved_blob_sha,
    )
    if not authorized:
        return SandboxResult(3, False, "", "notebook execution request is not authorized", False, False)
    try:
        payload = _load_trusted_blob(
            notebook, checked_out_commit_sha=checked_out_commit_sha,
            resolved_notebook_path=resolved_notebook_path, resolved_blob_sha=resolved_blob_sha,
        )
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return SandboxResult(3, False, "", "could not resolve the exact authorized notebook blob", False, False)
    if len(payload) > MAX_NOTEBOOK_BYTES or git_blob_sha1(payload) != resolved_blob_sha:
        return SandboxResult(3, False, "", "authorized notebook blob failed size or identity checks", False, False)
    valid, _, _ = read_notebook_redacted(payload)
    if not valid:
        return SandboxResult(3, False, "", "notebook failed structural validation", False, False)

    container_name = f"pc-notebook-{uuid.uuid4().hex}"
    with tempfile.TemporaryDirectory(prefix="pc-notebook-input-") as temp_input:
        input_dir = Path(temp_input)
        os.chmod(input_dir, 0o755)
        staged_input = input_dir / "input.ipynb"
        try:
            _write_exclusive(staged_input, payload, mode=0o644)
        except OSError:
            return SandboxResult(3, False, "", "could not stage exact notebook blob", False, False)
        command = build_sandbox_command(staged_input, container_name=container_name)
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            try:
                process = subprocess.Popen(
                    command, stdout=stdout_file, stderr=stderr_file, shell=False,
                    start_new_session=True, preexec_fn=_apply_output_limits,
                )
            except OSError as exc:
                return SandboxResult(127, False, "", f"{type(exc).__name__}: sandbox launch failed", False, False)
            timed_out = False
            try:
                return_code = int(process.wait(timeout=timeout_seconds))
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                _cleanup_container(container_name)
                return_code = 124
            raw_stdout, stdout_truncated = _read_bounded(stdout_file)
            stderr, stderr_truncated = _read_bounded(stderr_file)

    if return_code != 0 or timed_out:
        return SandboxResult(return_code, timed_out, raw_stdout, stderr, stdout_truncated, stderr_truncated)
    if stdout_truncated:
        return SandboxResult(3, False, "", "sandbox runner output exceeded 128 KiB", True, stderr_truncated)
    lines = [line for line in raw_stdout.splitlines() if line]
    if len(lines) != 2 or not lines[1].startswith("NOTEBOOK_ARTIFACT_BASE64="):
        return SandboxResult(3, False, lines[0] if lines else "", "sandbox runner did not stream the expected artifact", False, stderr_truncated)
    try:
        summary = json.loads(lines[0])
        artifact_payload = base64.b64decode(lines[1].split("=", 1)[1], validate=True)
    except (json.JSONDecodeError, ValueError):
        return SandboxResult(3, False, lines[0], "sandbox runner artifact stream was malformed", False, stderr_truncated)
    if len(artifact_payload) > MAX_NOTEBOOK_BYTES:
        return SandboxResult(3, False, lines[0], "executed notebook artifact exceeds 64 KiB", False, stderr_truncated)
    artifact_valid, artifact_doc, _ = read_notebook_redacted(artifact_payload)
    if not artifact_valid or artifact_doc is None:
        return SandboxResult(3, False, lines[0], "executed notebook artifact failed validation", False, stderr_truncated)
    sanitized = json.dumps(artifact_doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    execution_status = summary.get("status") if isinstance(summary, dict) else None
    if (
        len(sanitized) > MAX_NOTEBOOK_BYTES
        or execution_status not in {"completed", "cell_error"}
        or summary.get("artifact_bytes") != len(sanitized)
        or summary.get("artifact_sha256") != hashlib.sha256(sanitized).hexdigest()
    ):
        return SandboxResult(3, False, lines[0], "notebook artifact summary does not match validated bytes", False, stderr_truncated)
    final_path = destination / f"executed-{uuid.uuid4().hex}.ipynb"
    try:
        _write_exclusive(final_path, sanitized)
    except OSError:
        return SandboxResult(3, False, lines[0], "could not persist notebook artifact exclusively", False, stderr_truncated)
    return SandboxResult(return_code, False, lines[0], stderr, False, stderr_truncated, str(final_path), execution_status)
