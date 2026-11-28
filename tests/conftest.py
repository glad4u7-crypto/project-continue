"""Global safety fixtures for isolated pytest SQLite databases."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

import config
from database.connection import Database


@pytest.fixture(autouse=True)
def require_temporary_sqlite_databases(tmp_path, monkeypatch):
    """Prevent every test from opening the repository/default or production SQLite path."""
    root = tmp_path.resolve()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("PROJECT_CONTINUE_DB_BACKEND", "sqlite")
    monkeypatch.setenv("PROJECT_CONTINUE_DB", str(root / "default-test.sqlite3"))
    monkeypatch.setattr(config, "settings", config.Settings.from_env(os.environ))

    original_init = Database.__init__

    def guarded_init(self, path, *, timeout=5.0):
        if str(path) != ":memory:":
            candidate = Path(path).expanduser().resolve()
            try:
                candidate.relative_to(root)
            except ValueError as exc:
                raise AssertionError(
                    "SQLite tests must use pytest tmp_path or :memory:; "
                    "repository/default and production database paths are forbidden"
                ) from exc
        original_init(self, path, timeout=timeout)

    monkeypatch.setattr(Database, "__init__", guarded_init)

    runtime = sys.modules.get("database.runtime")
    if runtime is not None:
        runtime._repository_for_path.clear()
        runtime._postgres_repository_for_dsn.clear()
