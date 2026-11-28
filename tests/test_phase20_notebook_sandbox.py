import subprocess

import pytest

from scripts.phase20_notebook_sandbox import execute_notebook_sandbox


def test_execution_rejects_unpinned_image_before_docker(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("docker must not be called")
    monkeypatch.setattr(subprocess, "run", forbidden)
    notebook = tmp_path / "x.ipynb"
    notebook.write_text("{}", encoding="utf-8")
    policy = tmp_path / "allow.json"
    policy.write_text('{"schema_version":1,"entries":[]}', encoding="utf-8")
    with pytest.raises(PermissionError):
        execute_notebook_sandbox(tmp_path, "x.ipynb", current_commit="a"*40,
                                 requested_commit="a"*40, approval_id="review",
                                 policy_path=policy, image_id="phase20:latest")


def test_execution_rejects_commit_mismatch_before_docker(tmp_path, monkeypatch):
    def fake_run(args, **kwargs):
        if args[:3] == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, stdout="a"*40 + "\n", stderr="")
        raise AssertionError("docker must not be called")
    monkeypatch.setattr(subprocess, "run", fake_run)
    notebook = tmp_path / "x.ipynb"
    notebook.write_text("{}", encoding="utf-8")
    policy = tmp_path / "allow.json"
    policy.write_text('{"schema_version":1,"entries":[]}', encoding="utf-8")
    with pytest.raises(PermissionError):
        execute_notebook_sandbox(tmp_path, "x.ipynb", current_commit="a"*40,
                                 requested_commit="a"*40, approval_id="review",
                                 policy_path=policy, image_id="sha256:"+"a"*64)
