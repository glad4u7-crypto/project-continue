"""The pytest-wide SQLite path guard must reject non-temporary file databases."""
from pathlib import Path

import pytest

from database import Database


def test_database_guard_allows_tmp_path_and_private_memory(tmp_path):
    database = Database(tmp_path / "isolated.sqlite3")
    assert database.health_check() is True
    database.close()

    memory = Database(":memory:")
    assert memory.health_check() is True
    memory.close()


def test_database_guard_rejects_repository_and_production_paths(tmp_path):
    forbidden_paths = (
        Path.cwd() / ".data" / "project_continue.sqlite3",
        Path("/var/lib/project-continue/project_continue.sqlite3"),
    )
    for path in forbidden_paths:
        with pytest.raises(AssertionError, match="pytest tmp_path"):
            Database(path)
