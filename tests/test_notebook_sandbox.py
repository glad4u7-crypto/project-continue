from pathlib import Path

import pytest

from scripts.notebook_sandbox import SANDBOX_IMAGE, SANDBOX_UID, build_sandbox_command


def test_sandbox_uses_nonroot_readonly_and_bounded_container(tmp_path):
    notebook = tmp_path / "safe.ipynb"
    notebook.write_text("{}", encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()

    command = build_sandbox_command(notebook, output)

    assert command[:3] == ("docker", "run", "--rm")
    assert ("--user", f"{SANDBOX_UID}:{SANDBOX_UID}") == command[3:5]
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges" in command
    assert "--pids-limit=64" in command
    assert "--memory=512m" in command
    assert "--cpus=1" in command
    assert SANDBOX_IMAGE in command
    mounts = [command[index + 1] for index, value in enumerate(command[:-1]) if value == "--mount"]
    assert len(mounts) == 2
    assert mounts[0].endswith(",readonly")
    assert "/workspace/output" in mounts[1]


def test_sandbox_does_not_forward_host_secrets_or_production_mounts(tmp_path):
    notebook = tmp_path / "safe.ipynb"
    notebook.write_text("{}", encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()

    command = build_sandbox_command(notebook, output)
    rendered = " ".join(command).lower()

    for forbidden in ("github_token", "actions_runtime_token", "google_application_credentials",
                      "/content/drive", "mydrive", "--privileged", "--env"):
        assert forbidden not in rendered
    assert "--network" not in command  # Default-deny network is enforced in U20-7-08.


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
