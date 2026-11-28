"""Safe notebook inventory, validation, read and exclusive-create primitives.

This module never executes notebook code. All paths are confined to an explicit,
existing root; symlinks and hidden path components are rejected.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any

MAX_NOTEBOOK_BYTES = 256 * 1024
MAX_CELLS = 200
MAX_CELL_SOURCE_CHARS = 32 * 1024
MAX_OUTPUTS_PER_CELL = 20
MAX_OUTPUT_TEXT_CHARS = 16 * 1024
MAX_METADATA_DEPTH = 8
MAX_INVENTORY_ENTRIES = 500
MAX_INVENTORY_DEPTH = 4
_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)(\s*[=:]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)(-----BEGIN [A-Z ]*PRIVATE KEY-----)[\s\S]*?(-----END [A-Z ]*PRIVATE KEY-----)"),
)


def _safe_root(root: str | Path) -> Path:
    candidate = Path(root).expanduser()
    if candidate.is_symlink():
        raise ValueError("notebook root must not be a symlink")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError("notebook root must be an existing directory")
    return resolved


def _safe_relative(name: str) -> PurePosixPath:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise ValueError("invalid notebook path")
    rel = PurePosixPath(name)
    if rel.is_absolute() or any(part in ("", ".", "..") or part.startswith(".") for part in rel.parts):
        raise ValueError("notebook path traversal or hidden component rejected")
    if rel.suffix.lower() != ".ipynb":
        raise ValueError("only .ipynb files are supported")
    return rel


def _target(root: Path, name: str, *, must_exist: bool) -> Path:
    rel = _safe_relative(name)
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("symlink notebook paths are rejected")
    if must_exist:
        resolved = current.resolve(strict=True)
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise ValueError("notebook is not a regular file inside the configured root")
        return resolved
    parent = current.parent.resolve(strict=True)
    if not parent.is_relative_to(root) or not parent.is_dir():
        raise ValueError("notebook parent is outside the configured root")
    return parent / current.name


def _bounded_json(path: Path) -> tuple[dict[str, Any], bytes]:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_NOTEBOOK_BYTES:
        raise ValueError("notebook must be a regular file within the size limit")
    raw = path.read_bytes()
    if len(raw) > MAX_NOTEBOOK_BYTES:
        raise ValueError("notebook exceeds the size limit")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("notebook must contain valid UTF-8 JSON") from exc
    if not isinstance(document, dict):
        raise ValueError("notebook root must be a JSON object")
    return document, raw


def _check_depth(value: Any, depth: int = 0) -> None:
    if depth > MAX_METADATA_DEPTH:
        raise ValueError("notebook metadata nesting exceeds the limit")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError("metadata keys must be strings")
            _check_depth(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _check_depth(child, depth + 1)
    elif not isinstance(value, (str, int, float, bool, type(None))):
        raise ValueError("unsupported JSON value")


def validate_notebook_document(document: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(document, dict) or document.get("nbformat") != 4:
        raise ValueError("only nbformat 4 notebooks are accepted")
    minor = document.get("nbformat_minor")
    if not isinstance(minor, int) or isinstance(minor, bool) or not 0 <= minor <= 5:
        raise ValueError("unsupported nbformat minor version")
    cells = document.get("cells")
    if not isinstance(cells, list) or len(cells) > MAX_CELLS:
        raise ValueError("cells must be a bounded list")
    metadata = document.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("notebook metadata must be an object")
    _check_depth(metadata)
    for cell in cells:
        if not isinstance(cell, dict) or cell.get("cell_type") not in {"markdown", "code", "raw"}:
            raise ValueError("unsupported notebook cell")
        if not isinstance(cell.get("metadata", {}), dict):
            raise ValueError("cell metadata must be an object")
        _check_depth(cell.get("metadata", {}))
        source = cell.get("source", "")
        if isinstance(source, list):
            if not all(isinstance(part, str) for part in source):
                raise ValueError("cell source list must contain strings")
            source_text = "".join(source)
        elif isinstance(source, str):
            source_text = source
        else:
            raise ValueError("cell source must be text or a list of text")
        if len(source_text) > MAX_CELL_SOURCE_CHARS:
            raise ValueError("cell source exceeds the per-cell limit")
        if cell["cell_type"] == "code":
            outputs = cell.get("outputs", [])
            if not isinstance(outputs, list) or len(outputs) > MAX_OUTPUTS_PER_CELL:
                raise ValueError("code cell outputs exceed the limit")
            count = cell.get("execution_count")
            if count is not None and (not isinstance(count, int) or isinstance(count, bool) or count < 0):
                raise ValueError("invalid execution count")
            for output in outputs:
                if not isinstance(output, dict):
                    raise ValueError("invalid code cell output")
                output_type = output.get("output_type")
                if output_type not in {"stream", "display_data", "execute_result", "error"}:
                    raise ValueError("unsupported notebook output type")
                text_payload = output.get("text", "")
                if isinstance(text_payload, list):
                    if not all(isinstance(part, str) for part in text_payload):
                        raise ValueError("output text list must contain strings")
                    text_payload = "".join(text_payload)
                if not isinstance(text_payload, str) or len(text_payload) > MAX_OUTPUT_TEXT_CHARS:
                    raise ValueError("output text exceeds the limit")
                data = output.get("data", {})
                if not isinstance(data, dict):
                    raise ValueError("output data must be an object")
                for mime, payload in data.items():
                    if not isinstance(mime, str):
                        raise ValueError("invalid output MIME type")
                    if isinstance(payload, list):
                        if not all(isinstance(part, str) for part in payload):
                            raise ValueError("output text list must contain strings")
                        text_value = "".join(payload)
                    elif isinstance(payload, str):
                        text_value = payload
                    else:
                        continue
                    if len(text_value) > MAX_OUTPUT_TEXT_CHARS:
                        raise ValueError("individual output exceeds the limit")
    return {
        "valid": True,
        "nbformat": 4,
        "nbformat_minor": minor,
        "cell_count": len(cells),
        "code_cells": sum(c.get("cell_type") == "code" for c in cells),
    }


def inventory_notebooks(root: str | Path) -> dict[str, Any]:
    base = _safe_root(root)
    found: list[dict[str, Any]] = []
    examined = 0
    truncated = False
    stack = [(base, 0)]
    while stack:
        directory, depth = stack.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError:
            continue
        for entry in entries:
            if examined >= MAX_INVENTORY_ENTRIES:
                truncated = True
                stack.clear()
                break
            examined += 1
            if entry.name.startswith(".") or entry.is_symlink():
                continue
            path = Path(entry.path)
            try:
                if entry.is_dir(follow_symlinks=False):
                    if depth < MAX_INVENTORY_DEPTH:
                        stack.append((path, depth + 1))
                    continue
                if not entry.is_file(follow_symlinks=False) or path.suffix.lower() != ".ipynb":
                    continue
                info = entry.stat(follow_symlinks=False)
                if info.st_size > MAX_NOTEBOOK_BYTES:
                    status = "oversize"
                    digest = None
                else:
                    raw = path.read_bytes()
                    digest = hashlib.sha256(raw).hexdigest()
                    try:
                        doc = json.loads(raw.decode("utf-8"))
                        validate_notebook_document(doc)
                        status = "valid"
                    except (ValueError, UnicodeError, json.JSONDecodeError):
                        status = "invalid"
                found.append({
                    "path": path.relative_to(base).as_posix(),
                    "bytes": info.st_size,
                    "sha256": digest,
                    "status": status,
                })
            except OSError:
                continue
    return {"items": found, "examined": examined, "truncated": truncated}


def _redact(text: str) -> str:
    value = text
    for pattern in _SECRET_PATTERNS:
        if pattern.groups >= 3:
            value = pattern.sub(r"\1\2[REDACTED]", value)
        elif pattern.groups == 2:
            value = pattern.sub(r"\1[REDACTED]", value)
        else:
            value = pattern.sub("[REDACTED]", value)
    return value


def _redact_tree(value: Any, key: str = "") -> Any:
    if re.search(r"(?i)(token|password|secret|api[_-]?key|private[_-]?key)", key):
        return "[REDACTED]"
    if isinstance(value, str):
        return _redact(value)
    if isinstance(value, list):
        return [_redact_tree(item) for item in value]
    if isinstance(value, dict):
        return {str(item_key): _redact_tree(item_value, str(item_key))
                for item_key, item_value in value.items()}
    return value


def read_notebook(root: str | Path, name: str) -> dict[str, Any]:
    base = _safe_root(root)
    path = _target(base, name, must_exist=True)
    document, raw = _bounded_json(path)
    summary = validate_notebook_document(document)
    safe_document = _redact_tree(json.loads(json.dumps(document)))
    return {"notebook": safe_document, "summary": summary,
            "sha256": hashlib.sha256(raw).hexdigest()}


def create_notebook(root: str | Path, name: str, title: str | None = None) -> dict[str, Any]:
    base = _safe_root(root)
    target = _target(base, name, must_exist=False)
    heading = (title or Path(name).stem).strip()
    if not heading or len(heading) > 120 or any(ord(ch) < 32 for ch in heading):
        raise ValueError("invalid notebook title")
    document = {
        "cells": [
            {"cell_type": "markdown", "metadata": {}, "id": "project-continue-intro",
             "source": [f"# {heading}\n", "\n", "Review this notebook before running any code.\n"]},
            {"cell_type": "code", "execution_count": None, "metadata": {},
             "outputs": [], "id": "project-continue-first-cell", "source": []},
        ],
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python"}},
        "nbformat": 4, "nbformat_minor": 5,
    }
    validate_notebook_document(document)
    payload = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(payload) > MAX_NOTEBOOK_BYTES:
        raise ValueError("generated notebook exceeds size limit")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        verified, readback = _bounded_json(target)
        summary = validate_notebook_document(verified)
        if readback != payload:
            raise ValueError("notebook read-back mismatch")
    except Exception:
        try:
            target.unlink()
        except OSError:
            pass
        raise
    return {"path": target.relative_to(base).as_posix(), "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(), "summary": summary,
            "executed": False}
