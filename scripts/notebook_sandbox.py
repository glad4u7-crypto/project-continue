"""Build a minimal Docker invocation for an isolated notebook kernel.

This module only constructs an argv tuple; it never launches Docker itself.
The caller supplies a validated notebook file and a disposable output directory.
"""
from __future__ import annotations

from pathlib import Path

SANDBOX_IMAGE = "project-continue-notebook-sandbox:ci"
SANDBOX_UID = 10001


def _mount_path(path: Path) -> str:
    value = str(path)
    if any(character in value for character in (",", "\n", "\r")):
        raise ValueError("sandbox mount path contains unsupported characters")
    return value


def build_sandbox_command(notebook_path: str | Path, output_dir: str | Path) -> tuple[str, ...]:
    """Return fixed Docker argv with no inherited host environment or Drive mount."""
    notebook = Path(notebook_path).resolve(strict=True)
    output = Path(output_dir).resolve(strict=True)
    if not notebook.is_file():
        raise ValueError("notebook input must be a regular file")
    if notebook.suffix.lower() != ".ipynb":
        raise ValueError("notebook input must have an .ipynb extension")
    if not output.is_dir():
        raise ValueError("output path must be an existing directory")

    source = _mount_path(notebook)
    destination = _mount_path(output)
    return (
        "docker", "run", "--rm",
        "--user", f"{SANDBOX_UID}:{SANDBOX_UID}",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=64",
        "--memory=512m",
        "--cpus=1",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--mount", f"type=bind,src={source},dst=/workspace/input.ipynb,readonly",
        "--mount", f"type=bind,src={destination},dst=/workspace/output",
        "--workdir", "/workspace",
        SANDBOX_IMAGE,
        "python", "-m", "ipykernel", "--version",
    )
