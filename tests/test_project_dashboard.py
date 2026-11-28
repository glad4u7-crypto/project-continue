from pathlib import Path

from streamlit.testing.v1 import AppTest

import config
from config import Settings


def test_project_dashboard_renders_without_runtime_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_CONTINUE_DB", str(tmp_path / "dashboard.sqlite3"))
    monkeypatch.setattr(config, "settings", Settings.from_env({
        "APP_ENV": "test", "PROJECT_CONTINUE_DB": str(tmp_path / "dashboard.sqlite3")
    }))
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=15).run()

    assert not app.exception
    assert app.title[0].value == "🧭 Project Continue"
    assert any("No matching projects" in item.value for item in app.info)
