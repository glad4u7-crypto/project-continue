"""Build and supervise a constrained Docker notebook-kernel sandbox."""
from __future__ import annotations
import os
import re
import resource
import signal
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

SANDBOX_IMAGE = "project-continue-notebook-sandbox:ci"
SANDBOX_UID = 10001
EXECUTION_TIMEOUT_SECONDS = 120
MAX_OUTPUT_BYTES = 64 * 1024
_CONTAINER_NAME_RE = re.compile(r"^pc-notebook-[0-9a-f]{32}$")


@dataclass(frozen=True)
class SandboxResult:
    exit_code: int
    timed_out: bool
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool


def _mount_path(path: Path) -> str:
    value = str(path)
    if any(character in value for character in (",", "\\n", "\\r")):
        raise ValueError("sandbox mount path contains unsupported characters")
    return value


def build_sandbox_command(notebook_path: str | Path, output_dir: str | Path, *, container_name: str | None = None) -> tuple[str, ...]:
    """Return fixed Docker argv with network disabled and no host env/Drive mount."""
    notebook = Path(notebook_path).resolve(strict=True)
    output = Path(output_dir).resolve(strict=True)
    if not notebook.is_file():
        raise ValueError("notebook input must be a regular file")
    if notebook.suffix.lower() != ".ipynb":
        raise ValueError("notebook input must have an .ipynb extension")
    if not output.is_dir():
        raise ValueError("output path must be an existing directory")
    name = container_name or f"pc-notebook-{uuid.uuid4().hex}"
    if not isinstance(name, str) or not _CONTAINER_NAME_RE.fullmatch(name):
        raise ValueError("sandbox container name is invalid")
    source, destination = _mount_path(notebook), _mount_path(output)
    return (
        "docker", "run", "--rm", "--name", name, "--network=none", "--stop-timeout=5",
        "--user", f"{SANDBOX_UID}:{SANDBOX_UID}", "--read-only", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--pids-limit=64", "--memory=512m", "--cpus=1",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--mount", f"type=bind,src={source},dst=/workspace/input.ipynb,readonly",
        "--mount", f"type=bind,src={destination},dst=/workspace/output",
        "--workdir", "/workspace", SANDBOX_IMAGE,
        "python", "-m", "ipykernel", "--version",
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


def run_sandbox(notebook_path: str | Path, output_dir: str | Path, *, timeout_seconds: int = EXECUTION_TIMEOUT_SECONDS) -> SandboxResult:
    """Run the fixed sandbox probe; hard-kill the container when its deadline expires."""
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= EXECUTION_TIMEOUT_SECONDS:
        raise ValueError("sandbox timeout must be between 1 and 120 seconds")
    container_name = f"pc-notebook-{uuid.uuid4().hex}"
    command = build_sandbox_command(notebook_path, output_dir, container_name=container_name)
    timed_out = False
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        try:
            process = subprocess.Popen(command, stdout=stdout_file, stderr=stderr_file, shell=False, start_new_session=True, preexec_fn=_apply_output_limits)
        except OSError as exc:
            return SandboxResult(127, False, "", f"{type(exc).__name__}: sandbox launch failed", False, False)
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
    return SandboxResult(return_code, timed_out, stdout, stderr, stdout_truncated, stderr_truncated)
