from pathlib import Path

from scripts.colab_notebook_discovery import discover_project_files


def test_discovery_reports_counts_without_exposing_names(tmp_path):
    (tmp_path / "private-name.ipynb").write_text("{}", encoding="utf-8")
    (tmp_path / "module.py").write_text("print('ok')", encoding="utf-8")
    (tmp_path / "notes.md").write_text("# Notes", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("ignore", encoding="utf-8")

    passed, report = discover_project_files(repo_root=tmp_path, configured_root="")
    assert passed
    assert "notebooks=1" in report
    assert "python=1" in report
    assert "markdown=1" in report
    assert "private-name.ipynb" not in report
    assert "No paths or file contents were exported" in report


def test_discovery_supports_explicit_configured_folder(tmp_path):
    repo = tmp_path / "repo"
    drive_folder = tmp_path / "drive-project"
    repo.mkdir()
    drive_folder.mkdir()
    (drive_folder / "drive-notebook.ipynb").write_text("{}", encoding="utf-8")

    passed, report = discover_project_files(
        repo_root=repo, configured_root=str(drive_folder)
    )
    assert passed
    assert "configured_folder: notebooks=1" in report
    assert "drive-notebook.ipynb" not in report


def test_discovery_rejects_missing_configured_folder(tmp_path):
    passed, report = discover_project_files(
        repo_root=tmp_path, configured_root=str(tmp_path / "missing")
    )
    assert not passed
    assert "unavailable or unsafe" in report


def test_discovery_skips_hidden_files_and_symlinks(tmp_path):
    (tmp_path / ".hidden.ipynb").write_text("{}", encoding="utf-8")
    outside = tmp_path.parent / "outside.ipynb"
    outside.write_text("{}", encoding="utf-8")
    (tmp_path / "linked.ipynb").symlink_to(outside)

    passed, report = discover_project_files(repo_root=tmp_path, configured_root="")
    assert passed
    assert "notebooks=0" in report
