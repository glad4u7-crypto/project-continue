"""Global pytest safety gate: every file-backed SQLite DB stays under tmp_path."""
from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest


@pytest.fixture(autouse=True)
def enforce_temporary_sqlite_databases(monkeypatch, tmp_path):
    allowed_roots = (tmp_path.resolve(), Path(tempfile.gettempdir()).resolve())
    blocked_live_path = Path(os.environ.get("PROJECT_CONTINUE_DB", ".data/project_continue.sqlite3")).expanduser().resolve()
    original_connect = sqlite3.connect

    def guarded_connect(database, *args, **kwargs):
        value = str(database)
        uri = bool(kwargs.get("uri", False))
        if value == ":memory:" or (uri and "mode=memory" in value):
            return original_connect(database, *args, **kwargs)
        if uri and value.startswith("file:"):
            parsed = urlsplit(value)
            raw_path = unquote(parsed.path)
            candidate = Path(raw_path).resolve()
        else:
            candidate = Path(value).expanduser().resolve()
        if candidate == blocked_live_path or not any(
            candidate.is_relative_to(root) for root in allowed_roots
        ):
            raise RuntimeError(
                "Tests may only open temporary SQLite databases; the configured live database is blocked"
            )
        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", guarded_connect)
