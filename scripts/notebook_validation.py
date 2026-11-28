"""Bounded, non-executing validation for untrusted Jupyter notebook documents."""
from __future__ import annotations

import json
import re

MAX_NOTEBOOK_BYTES = 64 * 1024
MAX_CELLS = 200
MAX_CELL_SOURCE_BYTES = 32 * 1024
MAX_OUTPUTS_PER_CELL = 100
SUPPORTED_NBFORMAT_MAJOR = 4
MAX_NBFORMAT_MINOR = 5
_CELL_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_OUTPUT_TYPES = {"stream", "display_data", "execute_result", "error"}


def validate_notebook_payload(payload: bytes) -> tuple[bool, tuple[str, ...]]:
    """Validate notebook structure and resource bounds without executing cells.

    Error messages describe structural problems only; notebook source/output
    contents are never returned or logged.
    """
    errors: list[str] = []
    if not isinstance(payload, bytes):
        return False, ("payload must be bytes",)
    if len(payload) > MAX_NOTEBOOK_BYTES:
        return False, ("notebook exceeds the 64 KiB size limit",)
    try:
        text = payload.decode("utf-8", errors="strict")
        document = json.loads(
            text,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"invalid JSON constant: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return False, ("notebook is not valid strict UTF-8 JSON",)

    if not isinstance(document, dict):
        return False, ("notebook root must be an object",)
    if document.get("nbformat") != SUPPORTED_NBFORMAT_MAJOR:
        errors.append("unsupported nbformat major version")
    minor = document.get("nbformat_minor")
    if isinstance(minor, bool) or not isinstance(minor, int) or not 0 <= minor <= MAX_NBFORMAT_MINOR:
        errors.append("unsupported or invalid nbformat minor version")
    if not isinstance(document.get("metadata"), dict):
        errors.append("notebook metadata must be an object")

    cells = document.get("cells")
    if not isinstance(cells, list):
        errors.append("notebook cells must be an array")
        return False, tuple(errors)
    if len(cells) > MAX_CELLS:
        errors.append("notebook exceeds the 200-cell limit")

    seen_ids: set[str] = set()
    for index, cell in enumerate(cells[:MAX_CELLS]):
        prefix = f"cell {index}"
        if not isinstance(cell, dict):
            errors.append(f"{prefix} must be an object")
            continue
        cell_type = cell.get("cell_type")
        if cell_type not in {"markdown", "code", "raw"}:
            errors.append(f"{prefix} has an unsupported cell type")
        cell_metadata = cell.get("metadata", {})
        if not isinstance(cell_metadata, dict):
            errors.append(f"{prefix} metadata must be an object")
        source = cell.get("source")
        if isinstance(source, str):
            source_bytes = len(source.encode("utf-8"))
        elif isinstance(source, list) and all(isinstance(part, str) for part in source):
            source_bytes = sum(len(part.encode("utf-8")) for part in source)
        else:
            source_bytes = MAX_CELL_SOURCE_BYTES + 1
            errors.append(f"{prefix} source must be a string or an array of strings")
        if source_bytes > MAX_CELL_SOURCE_BYTES:
            errors.append(f"{prefix} source exceeds the 32 KiB limit")

        cell_id = cell.get("id")
        if minor >= 5:
            if not isinstance(cell_id, str) or not _CELL_ID_RE.fullmatch(cell_id):
                errors.append(f"{prefix} requires a valid nbformat 4.5 cell id")
            elif cell_id in seen_ids:
                errors.append(f"{prefix} has a duplicate cell id")
        if isinstance(cell_id, str):
            seen_ids.add(cell_id)

        if cell_type == "code":
            execution_count = cell.get("execution_count")
            if execution_count is not None and (
                isinstance(execution_count, bool)
                or not isinstance(execution_count, int)
                or execution_count < 0
            ):
                errors.append(f"{prefix} has an invalid execution_count")
            outputs = cell.get("outputs")
            if not isinstance(outputs, list):
                errors.append(f"{prefix} outputs must be an array")
                continue
            if len(outputs) > MAX_OUTPUTS_PER_CELL:
                errors.append(f"{prefix} exceeds the 100-output limit")
            for output_index, output in enumerate(outputs[:MAX_OUTPUTS_PER_CELL]):
                op = f"{prefix} output {output_index}"
                if not isinstance(output, dict) or output.get("output_type") not in _OUTPUT_TYPES:
                    errors.append(f"{op} has an invalid output type")
                    continue
                kind = output["output_type"]
                if kind == "stream":
                    text_value = output.get("text")
                    if not isinstance(text_value, (str, list)) or (
                        isinstance(text_value, list)
                        and not all(isinstance(part, str) for part in text_value)
                    ):
                        errors.append(f"{op} stream text is invalid")
                elif kind in {"display_data", "execute_result"}:
                    if not isinstance(output.get("data"), dict):
                        errors.append(f"{op} data must be an object")
                    if not isinstance(output.get("metadata"), dict):
                        errors.append(f"{op} metadata must be an object")
                elif kind == "error":
                    if not all(isinstance(output.get(key), str) for key in ("ename", "evalue")):
                        errors.append(f"{op} error fields are invalid")
                    if not isinstance(output.get("traceback"), list) or not all(
                        isinstance(line, str) for line in output.get("traceback", [])
                    ):
                        errors.append(f"{op} traceback is invalid")
        elif "outputs" in cell or "execution_count" in cell:
            errors.append(f"{prefix} non-code cell contains code execution fields")

    return not errors, tuple(errors)
