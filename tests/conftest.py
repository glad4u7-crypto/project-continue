"""Global safety fixtures for isolated pytest SQLite databases."""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
from dotenv import dotenv_values, load_dotenv

# Capture configured application storage before replacing the test environment.
# This includes exported variables and non-secret database settings from .env.
load_dotenv(override=False)
_ORIGINAL_DATABASE_SETTING = os.environ.get("PROJECT_CONTINUE_DB")
_DOTENV_DATABASE_SETTING = dotenv_values(".env").get("PROJECT_CONTINUE_DB")
_TEST_DATABASE_ROOT = Path(tempfile.mkdtemp(prefix="project-continue-pytest-")).resolve()


def _canonical_database_path(value: object) -> Path | None:
    """Normalize SQLite filename/URI arguments without opening the database."""
    if isinstance(value, os.PathLike):
        value = os.fspath(value)
    if not isinstance(value, str) or not value or value == ":memory:":
        return None
    if value.startswith("file:"):
        parsed = urlsplit(value)
        query = dict(part.split("=", 1) if "=" in part else (part, "") for part in parsed.query.split("&") if part)
        if query.get("mode") == "memory":
            return None
        raw_path = unquote(parsed.path)
        if not raw_path:
            raw_path = unquote(parsed.netloc)
        value = raw_path
    if not value:
        return None
    return Path(value).expanduser().resolve()


def _protected_live_database_paths() -> frozenset[Path]:
    candidates: set[Path] = {
        (Path.cwd() / ".data" / "project_continue.sqlite3").resolve(),
        Path("/var/lib/project-continue/project_continue.sqlite3").resolve(),
    }
    for configured in (_ORIGINAL_DATABASE_SETTING, _DOTENV_DATABASE_SETTING):
        normalized = _canonical_database_path(configured)
        if normalized is not None:
            candidates.add(normalized)
    return frozenset(candidates)


_PROTECTED_DATABASE_PATHS = _protected_live_database_paths()
os.environ["APP_ENV"] = "test"
os.environ["PROJECT_CONTINUE_DB_BACKEND"] = "sqlite"
os.environ["PROJECT_CONTINUE_DB"] = str(_TEST_DATABASE_ROOT / "session-default.sqlite3")

import config
from database.connection import Database


def _assert_database_path_is_not_live(value: object) -> None:
    candidate = _canonical_database_path(value)
    if candidate is None:
        return
    protected = set(_PROTECTED_DATABASE_PATHS)
    protected.update(
        Path(str(path) + suffix)
        for path in _PROTECTED_DATABASE_PATHS
        for suffix in ("-wal", "-shm", "-journal")
    )
    if candidate in protected:
        raise AssertionError(
            "pytest is forbidden from opening the configured live/default SQLite database "
            "or its journal files, including read-only and URI access"
        )


@pytest.fixture(autouse=True)
def require_temporary_sqlite_databases(tmp_path, monkeypatch):
    """Block live SQLite paths at both Database and sqlite3 connection boundaries."""
    root = tmp_path.resolve()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("PROJECT_CONTINUE_DB_BACKEND", "sqlite")
    monkeypatch.setenv("PROJECT_CONTINUE_DB", str(root / "default-test.sqlite3"))
    monkeypatch.setattr(config, "settings", config.Settings.from_env(os.environ))

    original_init = Database.__init__

    def guarded_init(self, path, *, timeout=5.0):
        _assert_database_path_is_not_live(path)
        if str(path) != ":memory:":
            candidate = Path(path).expanduser().resolve()
            if not any(_is_relative_to(candidate, allowed) for allowed in (root, _TEST_DATABASE_ROOT, Path(tempfile.gettempdir()).resolve())):
                raise AssertionError(
                    "SQLite tests must use pytest tmp_path, the temporary pytest session root, "
                    "or :memory:; repository/default and production database paths are forbidden"
                )
        original_init(self, path, timeout=timeout)

    original_connect = sqlite3.connect

    def guarded_connect(database, *args, **kwargs):
        _assert_database_path_is_not_live(database)
        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr(Database, "__init__", guarded_init)
    monkeypatch.setattr(sqlite3, "connect", guarded_connect)

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
