"""Global pytest safety gate: every file-backed SQLite DB stays under tmp_path."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest


@pytest.fixture(autouse=True)
def enforce_temporary_sqlite_databases(monkeypatch, tmp_path):
    allowed_root = tmp_path.resolve()
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
        if not candidate.is_relative_to(allowed_root):
            raise RuntimeError(
                "Tests may only open file-backed SQLite databases under pytest tmp_path"
            )
        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", guarded_connect)
