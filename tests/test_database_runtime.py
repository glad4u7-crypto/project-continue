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
