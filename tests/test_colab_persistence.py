from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "colab_persistence.py"
SPEC = importlib.util.spec_from_file_location("colab_persistence", SCRIPT)
assert SPEC and SPEC.loader
persistence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(persistence)


def test_sqlite_snapshot_is_integrity_checked_and_hashable(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO items(value) VALUES ('preserved')")
    target = tmp_path / "backup" / "copy.sqlite3"

    record = persistence.make_sqlite_snapshot(source, target)

    assert record["integrity_check"] == "ok"
    assert record["sha256"] == persistence.sha256(target)
    assert persistence.sqlite_check(target) == "ok"
    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT value FROM items").fetchone()[0] == "preserved"


def test_notebook_discovery_validates_json_and_hashes(tmp_path: Path) -> None:
    notebook = tmp_path / "nested" / "sample.ipynb"
    notebook.parent.mkdir()
    notebook.write_text(json.dumps({"cells": [{"cell_type": "code"}]}), encoding="utf-8")

    records = persistence.discover_notebooks(tmp_path)

    assert len(records) == 1
    assert records[0]["json_valid"] is True
    assert records[0]["cells"] == 1
    assert records[0]["sha256"] == persistence.sha256(notebook)


def test_copy_if_missing_never_overwrites_existing_file(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    target = tmp_path / "target.txt"
    source.write_text("new", encoding="utf-8")
    target.write_text("keep", encoding="utf-8")

    copied = persistence.copy_if_missing(source, target)

    assert copied is False
    assert target.read_text(encoding="utf-8") == "keep"
