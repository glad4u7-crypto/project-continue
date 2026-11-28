"""Build and supervise a constrained, identity-bound Docker notebook runner."""
from __future__ import annotations
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
MAX_OUTPUT_BYTES = 64 * 1024
MAX_NOTEBOOK_BYTES = 64 * 1024
_CONTAINER_NAME_RE = re.compile(r"^pc-notebook-[0-9a-f]{32}$")


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


def _mount_path(path: Path) -> str:
    value = str(path)
    if any(character in value for character in (",", "\n", "\r")):
        raise ValueError("sandbox mount path contains unsupported characters")
    return value


def build_sandbox_command(notebook_path: str | Path, output_dir: str | Path, *, container_name: str | None = None) -> tuple[str, ...]:
    """Return fixed Docker argv with network disabled and no host env/Drive mount."""
    raw_notebook, raw_output = Path(notebook_path), Path(output_dir)
    if raw_notebook.is_symlink() or raw_output.is_symlink():
        raise ValueError("sandbox paths must not be symlinks")
    notebook, output = raw_notebook.resolve(strict=True), raw_output.resolve(strict=True)
    if not notebook.is_file() or notebook.suffix.lower() != ".ipynb":
        raise ValueError("notebook input must be a regular .ipynb file")
    if not output.is_dir():
        raise ValueError("output path must be an existing directory")
    name = container_name or f"pc-notebook-{uuid.uuid4().hex}"
    if not isinstance(name, str) or not _CONTAINER_NAME_RE.fullmatch(name):
        raise ValueError("sandbox container name is invalid")
    return (
        "docker", "run", "--rm", "--name", name, "--network=none", "--stop-timeout=5",
        "--user", f"{SANDBOX_UID}:{SANDBOX_UID}", "--read-only", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--pids-limit=64", "--memory=512m", "--cpus=1",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--mount", f"type=bind,src={_mount_path(notebook)},dst=/workspace/input.ipynb,readonly",
        "--mount", f"type=bind,src={_mount_path(output)},dst=/workspace/output",
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


def _write_exclusive(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
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
        payload = notebook.read_bytes()
    except OSError:
        return SandboxResult(3, False, "", "notebook or output path is unavailable", False, False)
    if len(payload) > MAX_NOTEBOOK_BYTES:
        return SandboxResult(3, False, "", "notebook exceeds the 64 KiB input limit", False, False)
    actual_blob_sha = git_blob_sha1(payload)
    if actual_blob_sha != resolved_blob_sha:
        return SandboxResult(3, False, "", "resolved notebook blob does not match file bytes", False, False)
    authorized, _ = authorize_notebook_execution(
        request, checked_out_commit_sha=checked_out_commit_sha,
        resolved_notebook_path=resolved_notebook_path, resolved_blob_sha=actual_blob_sha,
    )
    if not authorized:
        return SandboxResult(3, False, "", "notebook execution request is not authorized", False, False)
    valid, _, _ = read_notebook_redacted(payload)
    if not valid:
        return SandboxResult(3, False, "", "notebook failed structural validation", False, False)

    container_name = f"pc-notebook-{uuid.uuid4().hex}"
    with tempfile.TemporaryDirectory(prefix="pc-notebook-output-") as temp_output:
        temp_dir = Path(temp_output)
        os.chmod(temp_dir, 0o777)
        command = build_sandbox_command(notebook, temp_dir, container_name=container_name)
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            try:
                process = subprocess.Popen(command, stdout=stdout_file, stderr=stderr_file,
                    shell=False, start_new_session=True, preexec_fn=_apply_output_limits)
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
            stdout, stdout_truncated = _read_bounded(stdout_file)
            stderr, stderr_truncated = _read_bounded(stderr_file)

        artifact_path = None
        execution_status = None
        raw_artifact = temp_dir / "executed.ipynb"
        if return_code == 0 and raw_artifact.is_file():
            if raw_artifact.stat().st_size > MAX_NOTEBOOK_BYTES:
                return SandboxResult(3, timed_out, stdout, "executed notebook artifact exceeds 64 KiB", stdout_truncated, stderr_truncated)
            artifact_valid, artifact_doc, _ = read_notebook_redacted(raw_artifact.read_bytes())
            if not artifact_valid or artifact_doc is None:
                return SandboxResult(3, timed_out, stdout, "executed notebook artifact failed validation", stdout_truncated, stderr_truncated)
            try:
                summary = json.loads(stdout)
            except (json.JSONDecodeError, TypeError):
                summary = {}
            execution_status = summary.get("status") if isinstance(summary, dict) else None
            sanitized = json.dumps(artifact_doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            if len(sanitized) > MAX_NOTEBOOK_BYTES:
                return SandboxResult(3, timed_out, stdout, "redacted notebook artifact exceeds 64 KiB", stdout_truncated, stderr_truncated)
            final_path = destination / f"executed-{uuid.uuid4().hex}.ipynb"
            try:
                _write_exclusive(final_path, sanitized)
            except OSError:
                return SandboxResult(3, timed_out, stdout, "could not persist notebook artifact exclusively", stdout_truncated, stderr_truncated)
            artifact_path = str(final_path)
    return SandboxResult(return_code, timed_out, stdout, stderr, stdout_truncated, stderr_truncated, artifact_path, execution_status)
