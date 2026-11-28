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

def test_untrusted_unhashable_schema_values_fail_closed():
    document = _document()
    document["cells"][0]["cell_type"] = []
    passed, errors = validate_notebook_payload(_payload(document))
    assert not passed
    assert errors

    document = _document()
    document["nbformat_minor"] = "5"
    passed, errors = validate_notebook_payload(_payload(document))
    assert not passed
    assert errors

    document = _document()
    document["cells"][1]["outputs"] = [{"output_type": []}]
    passed, errors = validate_notebook_payload(_payload(document))
    assert not passed
    assert errors


def test_invalid_unicode_in_source_is_rejected_without_exception():
    payload = b'{"nbformat":4,"nbformat_minor":5,"metadata":{},"cells":[{"cell_type":"raw","id":"raw-01","metadata":{},"source":"\\ud800"}]}'
    passed, errors = validate_notebook_payload(payload)
    assert not passed
    assert errors



def test_recovery_notebook_copy_contract_preserves_source_backup():
    import ast

    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "ProjectContinue-Recovery.ipynb"
    )
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_cells = [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]
    all_code = "\\n".join(code_cells)

    # The notebook may mount Drive normally, but must not force-remount it.
    assert "drive.mount('/content/drive')" in all_code
    assert "force_remount" not in all_code
    assert "drive.flush_and_unmount" not in all_code

    # Recovery copies the source tree to a distinct, timestamped destination.
    assert "BACKUP_ROOT = DRIVE_ROOT / 'Project-Continue-Backups'" in all_code
    assert "RESTORE_ROOT = DRIVE_ROOT / 'Project-Continue-Recovery-Restores'" in all_code
    assert "if RESTORE_DEST.exists():" in all_code
    assert "raise FileExistsError" in all_code
    assert "shutil.copytree(BACKUP_SOURCE, RESTORE_DEST, symlinks=False)" in all_code
    assert "BACKUP_SOURCE.exists()" in all_code
    assert "source_rel - restored_rel" in all_code

    # Fail closed if a future notebook edit adds a source-destructive call.
    forbidden_calls = {
        "unlink", "rmdir", "rmtree", "remove", "move", "rename", "replace",
    }
    for source in code_cells:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            called_name = (
                function.attr if isinstance(function, ast.Attribute)
                else function.id if isinstance(function, ast.Name)
                else ""
            )
            assert called_name not in forbidden_calls, (
                f"Recovery notebook contains source-destructive call: {called_name}"
            )
