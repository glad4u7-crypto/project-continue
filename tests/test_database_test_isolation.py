"""The pytest-wide SQLite path guard must reject non-temporary file databases."""
from pathlib import Path
import sqlite3
import tempfile

import pytest

from database import Database


def test_database_guard_allows_tmp_path_and_private_memory(tmp_path):
    database = Database(tmp_path / "isolated.sqlite3")
    assert database.health_check() is True
    database.close()

    memory = Database(":memory:")
    assert memory.health_check() is True
    memory.close()

    with tempfile.TemporaryDirectory() as temporary_root:
        temporary_database = Database(Path(temporary_root) / "temporary.sqlite3")
        assert temporary_database.health_check() is True
        temporary_database.close()


def test_database_guard_rejects_repository_and_production_paths(tmp_path):
    forbidden_paths = (
        Path.cwd() / ".data" / "project_continue.sqlite3",
        Path("/var/lib/project-continue/project_continue.sqlite3"),
    )
    for path in forbidden_paths:
        with pytest.raises(AssertionError, match="pytest tmp_path"):
            Database(path)



def test_sqlite_connection_boundary_blocks_live_paths_even_in_readonly_uri(tmp_path):
    live_database = (Path.cwd() / ".data" / "project_continue.sqlite3").resolve()
    with pytest.raises(AssertionError, match="configured live/default SQLite database"):
        sqlite3.connect(str(live_database))

    readonly_uri = f"file:{live_database}?mode=ro"
    with pytest.raises(AssertionError, match="configured live/default SQLite database"):
        sqlite3.connect(readonly_uri)

    alias = tmp_path / "live-database-alias.sqlite3"
    alias.symlink_to(live_database)
    with pytest.raises(AssertionError, match="configured live/default SQLite database"):
        sqlite3.connect(str(alias))


def test_sqlite_connection_boundary_blocks_live_database_journal_files():
    live_database = Path("/var/lib/project-continue/project_continue.sqlite3")
    for suffix in ("-wal", "-shm", "-journal"):
        with pytest.raises(AssertionError, match="configured live/default SQLite database"):
            sqlite3.connect(str(live_database) + suffix)


def test_sqlite_connection_boundary_still_allows_temporary_and_memory_databases(tmp_path):
    database = sqlite3.connect(tmp_path / "direct-sqlite.sqlite3")
    database.execute("CREATE TABLE sample (value INTEGER)")
    database.close()

    memory = sqlite3.connect(":memory:")
    assert memory.execute("SELECT 1").fetchone() == (1,)
    memory.close()
