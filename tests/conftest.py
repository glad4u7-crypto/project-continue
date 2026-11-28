"""Global safety fixtures for isolated pytest SQLite databases."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

_TEST_DATABASE_ROOT = Path(tempfile.mkdtemp(prefix="project-continue-pytest-")).resolve()
os.environ["APP_ENV"] = "test"
os.environ["PROJECT_CONTINUE_DB_BACKEND"] = "sqlite"
os.environ["PROJECT_CONTINUE_DB"] = str(_TEST_DATABASE_ROOT / "session-default.sqlite3")

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
            if not any(_is_relative_to(candidate, allowed) for allowed in (root, _TEST_DATABASE_ROOT, Path(tempfile.gettempdir()).resolve())):
                raise AssertionError(
                    "SQLite tests must use pytest tmp_path, the temporary pytest session root, "
                    "or :memory:; repository/default and production database paths are forbidden"
                )
        original_init(self, path, timeout=timeout)

    monkeypatch.setattr(Database, "__init__", guarded_init)

    runtime = sys.modules.get("database.runtime")
    if runtime is not None:
        runtime._repository_for_path.clear()
        runtime._postgres_repository_for_dsn.clear()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def pytest_sessionfinish(session, exitstatus):
    """Remove the shared temporary fallback database after the test session."""
    shutil.rmtree(_TEST_DATABASE_ROOT, ignore_errors=True)
