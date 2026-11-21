"""Streamlit application smoke tests using an isolated temporary database."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_dashboard_starts_with_isolated_database(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("PROJECT_CONTINUE_DB", str(tmp_path / "ui-smoke.sqlite3"))
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    app = AppTest.from_file(str(project_root / "app.py"), default_timeout=20).run()

    assert not app.exception
    assert any("Project Continue" in item.value for item in app.title)
    assert any("No matching projects" in item.value for item in app.info)
    assert any("GitHub repository is not configured" in item.value for item in app.warning)
