import json

import pytest

from scripts.phase20_notebooks import (
    MAX_NOTEBOOK_BYTES,
    create_notebook,
    inventory_notebooks,
    read_notebook,
    validate_notebook_document,
)


def notebook(source="print('ok')"):
    return {
        "cells": [{"cell_type": "code", "execution_count": None, "metadata": {},
                   "outputs": [], "source": source}],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4, "nbformat_minor": 5,
    }


def test_inventory_is_read_only_bounded_and_hashes_notebook(tmp_path):
    path = tmp_path / "safe.ipynb"
    path.write_text(json.dumps(notebook()), encoding="utf-8")
    hidden = tmp_path / ".private.ipynb"
    hidden.write_text(json.dumps(notebook()), encoding="utf-8")
    before = path.read_bytes()
    result = inventory_notebooks(tmp_path)
    assert [item["path"] for item in result["items"]] == ["safe.ipynb"]
    assert result["items"][0]["status"] == "valid"
    assert len(result["items"][0]["sha256"]) == 64
    assert path.read_bytes() == before
    assert ".private.ipynb" not in repr(result)


@pytest.mark.parametrize("document", [
    {"nbformat": 3, "nbformat_minor": 0, "cells": [], "metadata": {}},
    {"nbformat": 4, "nbformat_minor": 99, "cells": [], "metadata": {}},
    {"nbformat": 4, "nbformat_minor": 5, "cells": "not-list", "metadata": {}},
    {"nbformat": 4, "nbformat_minor": 5, "cells": [{"cell_type": "execute", "source": ""}], "metadata": {}},
])
def test_rejects_malformed_or_unsupported_notebook(document):
    with pytest.raises(ValueError):
        validate_notebook_document(document)


def test_rejects_cell_source_output_and_metadata_bounds():
    doc = notebook("x" * 32769)
    with pytest.raises(ValueError):
        validate_notebook_document(doc)
    doc = notebook()
    doc["cells"][0]["outputs"] = [{}] * 21
    with pytest.raises(ValueError):
        validate_notebook_document(doc)
    doc = notebook()
    doc["metadata"] = {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": {"i": 1}}}}}}}}}
    with pytest.raises(ValueError):
        validate_notebook_document(doc)


def test_rejects_oversized_notebook_file(tmp_path):
    path = tmp_path / "large.ipynb"
    path.write_bytes(b" " * (MAX_NOTEBOOK_BYTES + 1))
    with pytest.raises(ValueError):
        read_notebook(tmp_path, "large.ipynb")


def test_create_is_exclusive_and_readback_verified(tmp_path):
    result = create_notebook(tmp_path, "New.ipynb")
    assert result["executed"] is False
    assert result["summary"]["cell_count"] == 2
    original = (tmp_path / "New.ipynb").read_bytes()
    with pytest.raises(FileExistsError):
        create_notebook(tmp_path, "New.ipynb")
    assert (tmp_path / "New.ipynb").read_bytes() == original


def test_read_redacts_credentials_from_source_and_output(tmp_path):
    doc = notebook("api_key = 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456'")
    doc["cells"][0]["outputs"] = [{"output_type": "stream", "text": "Bearer abcdefghijklmnopqrstuvwxyz123456"}]
    (tmp_path / "secret.ipynb").write_text(json.dumps(doc), encoding="utf-8")
    result = read_notebook(tmp_path, "secret.ipynb")
    rendered = json.dumps(result["notebook"])
    assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456" not in rendered
    assert "abcdefghijklmnopqrstuvwxyz123456" not in rendered
    assert "[REDACTED]" in rendered


@pytest.mark.parametrize("name", ["../escape.ipynb", "/tmp/x.ipynb", ".hidden.ipynb", "a\\b.ipynb", "x.txt"])
def test_rejects_unsafe_names(tmp_path, name):
    with pytest.raises(ValueError):
        read_notebook(tmp_path, name)


def test_rejects_symlink_notebook(tmp_path):
    outside = tmp_path.parent / "outside.ipynb"
    outside.write_text(json.dumps(notebook()), encoding="utf-8")
    (tmp_path / "link.ipynb").symlink_to(outside)
    with pytest.raises(ValueError):
        read_notebook(tmp_path, "link.ipynb")


def test_create_refuses_symlink_collision(tmp_path):
    outside = tmp_path / "outside"
    outside.write_text("untouched", encoding="utf-8")
    (tmp_path / "linked.ipynb").symlink_to(outside)
    with pytest.raises(ValueError):
        create_notebook(tmp_path, "linked.ipynb")
    assert outside.read_text(encoding="utf-8") == "untouched"
