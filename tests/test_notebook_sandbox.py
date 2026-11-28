from pathlib import Path
import tempfile
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts import notebook_sandbox
from scripts.notebook_sandbox import (
    EXECUTION_TIMEOUT_SECONDS, SANDBOX_IMAGE, SANDBOX_UID,
    build_sandbox_command, run_sandbox,
)


def _fixtures(tmp_path):
    notebook = tmp_path / "safe.ipynb"
    notebook.write_text("{}", encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    return notebook, output


def test_sandbox_uses_nonroot_readonly_and_bounded_container(tmp_path):
    notebook, output = _fixtures(tmp_path)
    command = build_sandbox_command(notebook, output)
    assert command[:3] == ("docker", "run", "--rm")
    assert "--network=none" in command
    assert "--stop-timeout=5" in command
    assert ("--user", f"{SANDBOX_UID}:{SANDBOX_UID}") == command[7:9]
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges" in command
    assert "--pids-limit=64" in command
    assert "--memory=512m" in command
    assert "--cpus=1" in command
    assert SANDBOX_IMAGE in command
    mounts = [command[index + 1] for index, value in enumerate(command[:-1]) if value == "--mount"]
    assert len(mounts) == 2 and mounts[0].endswith(",readonly")
    assert "/workspace/output" in mounts[1]


def test_sandbox_does_not_forward_host_secrets_or_production_mounts(tmp_path):
    notebook, output = _fixtures(tmp_path)
    rendered = " ".join(build_sandbox_command(notebook, output)).lower()
    for forbidden in ("github_token", "actions_runtime_token", "google_application_credentials", "/content/drive", "mydrive", "--privileged", "--env"):
        assert forbidden not in rendered


def test_sandbox_rejects_non_notebook_and_missing_paths(tmp_path):
    wrong = tmp_path / "input.txt"
    wrong.write_text("not a notebook", encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(ValueError):
        build_sandbox_command(wrong, output)
    with pytest.raises(FileNotFoundError):
        build_sandbox_command(tmp_path / "missing.ipynb", output)


def test_sandbox_rejects_non_directory_output(tmp_path):
    notebook = tmp_path / "safe.ipynb"
    notebook.write_text("{}", encoding="utf-8")
    output = tmp_path / "not-a-directory"
    output.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        build_sandbox_command(notebook, output)


def test_timeout_is_bounded_and_rejects_invalid_values(tmp_path):
    notebook, output = _fixtures(tmp_path)
    for invalid in (0, -1, EXECUTION_TIMEOUT_SECONDS + 1, True, 1.5):
        with pytest.raises(ValueError):
            run_sandbox(notebook, output, timeout_seconds=invalid)


def test_sandbox_timeout_kills_process_group_and_container(tmp_path, monkeypatch):
    notebook, output = _fixtures(tmp_path)
    process = SimpleNamespace(pid=4321, wait=Mock(side_effect=[
        subprocess.TimeoutExpired(cmd="docker run", timeout=1), -9,
    ]))
    popen, killpg, cleanup = Mock(return_value=process), Mock(), Mock()
    monkeypatch.setattr(notebook_sandbox.subprocess, "Popen", popen)
    monkeypatch.setattr(notebook_sandbox.os, "killpg", killpg)
    monkeypatch.setattr(notebook_sandbox, "_cleanup_container", cleanup)
    result = run_sandbox(notebook, output, timeout_seconds=1)
    assert result.timed_out and result.exit_code == 124
    killpg.assert_called_once()
    cleanup.assert_called_once()
    assert popen.call_args.kwargs["shell"] is False
    assert popen.call_args.kwargs["start_new_session"] is True


def test_sandbox_output_reader_caps_and_marks_truncation():
    with tempfile.TemporaryFile() as stream:
        stream.write(b"x" * (notebook_sandbox.MAX_OUTPUT_BYTES + 1))
        text, truncated = notebook_sandbox._read_bounded(stream)
    assert len(text) == notebook_sandbox.MAX_OUTPUT_BYTES
    assert truncated
