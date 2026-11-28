from pathlib import Path
import sqlite3
import tempfile

import pytest


def test_pytest_runner_blocks_non_temporary_sqlite_database(tmp_path):
    with pytest.raises(RuntimeError, match="temporary SQLite"):
        sqlite3.connect(Path.home() / "project-continue-live.sqlite3")
    configured_live = Path(__file__).resolve().parents[1] / ".data" / "project_continue.sqlite3"
    with pytest.raises(RuntimeError, match="temporary SQLite"):
        sqlite3.connect(configured_live)


def test_pytest_runner_allows_pytest_tmp_path_temporary_directory_and_memory(tmp_path):
    with sqlite3.connect(tmp_path / "isolated.sqlite3") as connection:
        connection.execute("CREATE TABLE sample (id INTEGER)")
    with tempfile.TemporaryDirectory() as temporary:
        with sqlite3.connect(Path(temporary) / "isolated.sqlite3") as connection:
            connection.execute("CREATE TABLE sample (id INTEGER)")
    with sqlite3.connect(":memory:") as connection:
        assert connection.execute("SELECT 1").fetchone()[0] == 1
