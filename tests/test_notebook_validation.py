import json
from pathlib import Path

from scripts.notebook_validation import (
    MAX_NOTEBOOK_BYTES,
    validate_notebook_payload,
)


def _document():
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "id": "intro-01",
                "metadata": {},
                "source": ["# Safe notebook\n"],
            },
            {
                "cell_type": "code",
                "id": "code-01",
                "metadata": {},
                "execution_count": None,
                "outputs": [],
                "source": [],
            },
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _payload(document):
    return json.dumps(document, ensure_ascii=False).encode("utf-8")


def test_repository_recovery_notebook_passes_bounded_validation():
    path = Path(__file__).resolve().parents[1] / "notebooks" / "ProjectContinue-Recovery.ipynb"
    passed, errors = validate_notebook_payload(path.read_bytes())
    assert passed, errors


def test_valid_nbformat_45_document_passes():
    passed, errors = validate_notebook_payload(_payload(_document()))
    assert passed
    assert errors == ()


def test_malformed_json_and_invalid_utf8_are_rejected():
    assert not validate_notebook_payload(b"{not-json")[0]
    assert not validate_notebook_payload(b"\xff")[0]


def test_unsupported_nbformat_versions_are_rejected():
    document = _document()
    document["nbformat"] = 5
    assert not validate_notebook_payload(_payload(document))[0]
    document = _document()
    document["nbformat_minor"] = 6
    assert not validate_notebook_payload(_payload(document))[0]


def test_missing_or_duplicate_nbformat_45_cell_ids_are_rejected():
    document = _document()
    del document["cells"][0]["id"]
    assert not validate_notebook_payload(_payload(document))[0]
    document = _document()
    document["cells"][1]["id"] = document["cells"][0]["id"]
    assert not validate_notebook_payload(_payload(document))[0]


def test_invalid_cell_type_metadata_and_source_are_rejected():
    document = _document()
    document["cells"][0]["cell_type"] = "javascript"
    assert not validate_notebook_payload(_payload(document))[0]
    document = _document()
    document["cells"][0]["metadata"] = []
    assert not validate_notebook_payload(_payload(document))[0]
    document = _document()
    document["cells"][0]["source"] = [1, 2]
    assert not validate_notebook_payload(_payload(document))[0]


def test_cell_and_output_bounds_are_enforced():
    document = _document()
    document["cells"][1]["outputs"] = [
        {"output_type": "stream", "name": "stdout", "text": "x"}
    ] * 101
    passed, errors = validate_notebook_payload(_payload(document))
    assert not passed
    assert any("100-output limit" in error for error in errors)


def test_notebook_and_cell_source_size_limits_are_enforced():
    oversized = b" " * (MAX_NOTEBOOK_BYTES + 1)
    assert not validate_notebook_payload(oversized)[0]
    document = _document()
    document["cells"][0]["source"] = "x" * (32 * 1024 + 1)
    passed, errors = validate_notebook_payload(_payload(document))
    assert not passed
    assert any("32 KiB limit" in error for error in errors)


def test_non_code_cells_cannot_contain_execution_fields():
    document = _document()
    document["cells"][0]["outputs"] = []
    assert not validate_notebook_payload(_payload(document))[0]
