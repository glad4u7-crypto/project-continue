from pathlib import Path
import sqlite3

import pytest


def test_pytest_runner_blocks_non_temporary_sqlite_database(tmp_path):
    with pytest.raises(RuntimeError, match="pytest tmp_path"):
        sqlite3.connect(Path.home() / "project-continue-live.sqlite3")


def test_pytest_runner_allows_temporary_and_memory_databases(tmp_path):
    with sqlite3.connect(tmp_path / "isolated.sqlite3") as connection:
        connection.execute("CREATE TABLE sample (id INTEGER)")
    with sqlite3.connect(":memory:") as connection:
        assert connection.execute("SELECT 1").fetchone()[0] == 1
