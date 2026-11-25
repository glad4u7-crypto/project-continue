"""Tests for the shared Streamlit database resource."""
from database.runtime import _repository_for_path, get_project_repository


def test_repository_resource_is_cached_per_database_path(tmp_path):
    _repository_for_path.clear()
    path = str(tmp_path / "nested" / "shared.sqlite3")
    first = get_project_repository(path)
    second = get_project_repository(path)

    assert first is second
    assert first.database is second.database
    assert first.database.health_check() is True


def test_different_paths_receive_isolated_resources(tmp_path):
    _repository_for_path.clear()
    first = get_project_repository(tmp_path / "first.sqlite3")
    second = get_project_repository(tmp_path / "second.sqlite3")

    assert first is not second
    assert first.database is not second.database


def test_sqlite_remains_the_default_runtime_backend(tmp_path, monkeypatch):
    from config import Settings
    import database.runtime as runtime

    monkeypatch.setattr(runtime, "get_settings", lambda: Settings.from_env({
        "APP_ENV": "test", "PROJECT_CONTINUE_DB": str(tmp_path / "default.sqlite3")
    }))
    _repository_for_path.clear()
    repository = get_project_repository()
    assert repository.database.health_check() is True


def test_postgresql_runtime_selection_uses_explicit_configured_dsn(monkeypatch):
    from config import Settings
    import database.runtime as runtime

    monkeypatch.setattr(runtime, "get_settings", lambda: Settings.from_env({
        "APP_ENV": "test", "PROJECT_CONTINUE_DB_BACKEND": "postgresql",
        "PROJECT_CONTINUE_POSTGRES_DSN": "postgresql://user:pass@localhost/db"
    }))
    monkeypatch.setattr(runtime, "_postgres_repository_for_dsn", lambda dsn: ("postgresql", dsn))
    assert get_project_repository() == ("postgresql", "postgresql://user:pass@localhost/db")


def test_unknown_runtime_backend_is_rejected(monkeypatch):
    import pytest
    import database.runtime as runtime
    from config import Settings

    monkeypatch.setattr(runtime, "get_settings", lambda: Settings.from_env({"APP_ENV": "test"}))
    with pytest.raises(ValueError, match="sqlite or postgresql"):
        get_project_repository(backend="mysql")
