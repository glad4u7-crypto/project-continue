import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts import notebook_sandbox
from scripts.notebook_container_runner import summarize_notebook, write_artifact_exclusive
from scripts.notebook_sandbox import (
    EXECUTION_TIMEOUT_SECONDS, SANDBOX_IMAGE, SANDBOX_UID,
    build_sandbox_command, git_blob_sha1, run_sandbox,
)

RECOVERY_PATH = "notebooks/ProjectContinue-Recovery.ipynb"
RECOVERY_BLOB = "544c131c97101485c4f328f83de1f96e65162dad"
COMMIT = subprocess.run(("git", "rev-parse", "HEAD"), cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=True).stdout.strip()


def _fixtures(tmp_path):
    notebook = tmp_path / "safe.ipynb"
    notebook.write_text("{}", encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    return notebook, output


def _recovery_file():
    return Path(__file__).resolve().parents[1] / "notebooks" / "ProjectContinue-Recovery.ipynb"


def _request():
    return {"notebook_path": RECOVERY_PATH, "commit_sha": COMMIT, "blob_sha": RECOVERY_BLOB}


def test_sandbox_uses_nonroot_readonly_and_bounded_container(tmp_path):
    notebook, output = _fixtures(tmp_path)
    command = build_sandbox_command(notebook)
    assert command[:2] == ("docker", "run")
    assert "--rm" not in command
    assert "--network=none" in command
    assert "--stop-timeout=5" in command
    assert ("--user", f"{SANDBOX_UID}:{SANDBOX_UID}") == command[6:8]
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges" in command
    assert "--pids-limit=64" in command
    assert "--memory=512m" in command
    assert "--cpus=1" in command
    assert SANDBOX_IMAGE in command
    assert "scripts.notebook_container_runner" in command
    mounts = [command[index + 1] for index, value in enumerate(command[:-1]) if value == "--mount"]
    assert len(mounts) == 1 and mounts[0].endswith(",readonly")
    assert any(value.startswith("/workspace/output:") and "size=1m" in value for value in command)


def test_sandbox_does_not_forward_host_secrets_or_production_mounts(tmp_path):
    notebook, output = _fixtures(tmp_path)
    rendered = " ".join(build_sandbox_command(notebook)).lower()
    for forbidden in ("github_token", "actions_runtime_token", "google_application_credentials",
                      "/content/drive", "mydrive", "--privileged", "--env"):
        assert forbidden not in rendered


def test_sandbox_rejects_non_notebook_and_missing_paths(tmp_path):
    wrong = tmp_path / "input.txt"
    wrong.write_text("not a notebook", encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(ValueError):
        build_sandbox_command(wrong)
    with pytest.raises(FileNotFoundError):
        build_sandbox_command(tmp_path / "missing.ipynb")


def test_sandbox_rejects_container_name_injection(tmp_path):
    notebook, output = _fixtures(tmp_path)
    with pytest.raises(ValueError):
        build_sandbox_command(notebook, container_name="--privileged")


def test_git_blob_sha_matches_reviewed_notebook_blob():
    payload = notebook_sandbox._load_trusted_blob(
        _recovery_file(), checked_out_commit_sha=COMMIT,
        resolved_notebook_path=RECOVERY_PATH, resolved_blob_sha=RECOVERY_BLOB,
    )
    assert git_blob_sha1(payload) == RECOVERY_BLOB


def test_timeout_is_bounded_and_rejects_invalid_values(tmp_path):
    for invalid in (0, -1, EXECUTION_TIMEOUT_SECONDS + 1, True, 1.5):
        with pytest.raises(ValueError):
            run_sandbox(
                _recovery_file(), tmp_path, request=_request(),
                checked_out_commit_sha=COMMIT, resolved_notebook_path=RECOVERY_PATH,
                resolved_blob_sha=RECOVERY_BLOB, timeout_seconds=invalid,
            )


def test_sandbox_timeout_kills_process_group_and_container(tmp_path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    process = SimpleNamespace(pid=4321, wait=Mock(side_effect=[
        subprocess.TimeoutExpired(cmd="docker run", timeout=1), -9,
    ]))
    popen, killpg, cleanup = Mock(return_value=process), Mock(), Mock()
    monkeypatch.setattr(notebook_sandbox, "_load_trusted_blob", lambda *args, **kwargs: _recovery_file().read_bytes())
    monkeypatch.setattr(notebook_sandbox.subprocess, "Popen", popen)
    monkeypatch.setattr(notebook_sandbox.os, "killpg", killpg)
    monkeypatch.setattr(notebook_sandbox, "_cleanup_container", cleanup)
    result = run_sandbox(
        _recovery_file(), output, request=_request(),
        checked_out_commit_sha=COMMIT, resolved_notebook_path=RECOVERY_PATH,
        resolved_blob_sha=RECOVERY_BLOB, timeout_seconds=1,
    )
    assert result.timed_out and result.exit_code == 124
    killpg.assert_called_once()
    cleanup.assert_called_once()
    assert popen.call_args.kwargs["shell"] is False
    assert popen.call_args.kwargs["start_new_session"] is True


def test_sandbox_rejects_unapproved_identity_before_launch(tmp_path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    popen = Mock()
    monkeypatch.setattr(notebook_sandbox.subprocess, "Popen", popen)
    result = run_sandbox(
        _recovery_file(), output, request={"notebook_path": "notebooks/other.ipynb"},
        checked_out_commit_sha=COMMIT, resolved_notebook_path=RECOVERY_PATH,
        resolved_blob_sha=RECOVERY_BLOB,
    )
    assert result.exit_code == 3 and "not authorized" in result.stderr
    popen.assert_not_called()


def test_sandbox_rejects_changed_input_bytes_before_launch(tmp_path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    popen = Mock()
    monkeypatch.setattr(notebook_sandbox.subprocess, "Popen", popen)
    result = run_sandbox(
        _recovery_file(), output, request=_request(),
        checked_out_commit_sha=COMMIT, resolved_notebook_path=RECOVERY_PATH,
        resolved_blob_sha="b" * 40,
    )
    assert result.exit_code == 3 and "not authorized" in result.stderr
    popen.assert_not_called()


def test_artifact_summary_counts_execution_and_traceback_cells():
    document = {
        "cells": [
            {"cell_type": "code", "execution_count": 1, "outputs":[
                {"output_type": "stream", "text": "hello"}]},
            {"cell_type": "code", "execution_count": 2, "outputs":[
                {"output_type": "error", "ename": "ValueError", "evalue": "bad",
                 "traceback": ["ValueError: bad"]}]},
            {"cell_type": "markdown", "source": "text"},
        ],
    }
    summary = summarize_notebook(document, "cell_error", 123, "f" * 64)
    assert summary["executed_code_cells"] == 2
    assert summary["error_cells"] == 1
    assert summary["status"] == "cell_error"


def test_artifact_writer_is_exclusive_and_size_bounded(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    path = output / "executed.ipynb"
    document = {"cells": [{"cell_type": "code", "execution_count": 1, "outputs": [
        {"output_type": "error", "ename": "ValueError", "evalue": "bad",
         "traceback": ["Traceback (most recent call last):", "ValueError: bad"]}
    ]}]}
    payload = json.dumps(document).encode("utf-8")
    write_artifact_exclusive(path, payload, output_root=output)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["cells"][0]["execution_count"] == 1
    assert saved["cells"][0]["outputs"][0]["traceback"][-1] == "ValueError: bad"
    with pytest.raises(FileExistsError):
        write_artifact_exclusive(path, b'{"changed":true}', output_root=output)
    with pytest.raises(ValueError):
        write_artifact_exclusive(output / "another.ipynb", b"{}", output_root=output)
    with pytest.raises(ValueError):
        write_artifact_exclusive(output / "executed.ipynb", b"x" * (64 * 1024 + 1), output_root=output)

def test_successful_runner_copies_and_persists_redacted_execution_artifact(tmp_path, monkeypatch):
    import hashlib

    output = tmp_path / "output"
    output.mkdir()
    document = {
        "cells": [{
            "cell_type": "code", "id": "cell-01", "metadata": {},
            "execution_count": 1, "source": "print('hello')",
            "outputs": [{"output_type": "stream", "name": "stdout", "text": "hello\\n"}],
        }],
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}},
        "nbformat": 4, "nbformat_minor": 5,
    }
    payload = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    summary = summarize_notebook(document, "completed", len(payload), hashlib.sha256(payload).hexdigest())

    process = SimpleNamespace(pid=1234, wait=Mock(return_value=0))
    def fake_popen(command, **kwargs):
        mount = command[command.index("--mount") + 1]
        staged_path = Path(mount.split(",dst=", 1)[0].removeprefix("type=bind,src="))
        assert staged_path.read_bytes() == _recovery_file().read_bytes()
        assert staged_path.stat().st_mode & 0o777 == 0o644
        kwargs["stdout"].write(json.dumps(summary).encode("utf-8"))
        kwargs["stdout"].flush()
        return process

    def fake_run(command, **kwargs):
        if command[1] == "cp":
            Path(command[-1]).write_bytes(payload)
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(notebook_sandbox, "_load_trusted_blob", lambda *args, **kwargs: _recovery_file().read_bytes())
    monkeypatch.setattr(notebook_sandbox.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(notebook_sandbox.subprocess, "run", fake_run)
    result = run_sandbox(
        _recovery_file(), output, request=_request(),
        checked_out_commit_sha=COMMIT, resolved_notebook_path=RECOVERY_PATH,
        resolved_blob_sha=RECOVERY_BLOB,
    )
    assert result.exit_code == 0
    assert result.execution_status == "completed"
    assert result.artifact_path is not None
    saved = json.loads(Path(result.artifact_path).read_text(encoding="utf-8"))
    assert saved["cells"][0]["execution_count"] == 1
    assert saved["cells"][0]["outputs"][0]["text"] == "hello\\n"
