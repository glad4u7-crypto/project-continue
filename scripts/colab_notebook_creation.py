"""Create a minimal Colab notebook in an explicitly configured folder.

Creation is bounded, non-overwriting, and does not execute notebook code.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path

MAX_NOTEBOOK_BYTES = 64 * 1024
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,63}$")


def _safe_directory(value: str | Path | None) -> Path | None:
    if value is None or not str(value).strip():
        return None
    candidate = Path(value).expanduser()
    try:
        if candidate.is_symlink():
            return None
        resolved = candidate.resolve(strict=True)
        if not resolved.is_dir():
            return None
        return resolved
    except (OSError, RuntimeError):
        return None


def _notebook_document(title: str) -> dict:
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "id": "project-continue-intro",
                "source": [
                    f"# {title}\n",
                    "\n",
                    "Created by Project Continue. Review this notebook before running any code.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "id": "project-continue-first-cell",
                "source": [],
            },
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def create_notebook(notebook_name: str, configured_root: str | Path | None = None) -> tuple[bool, str]:
    """Create one starter .ipynb; refuse unsafe paths and every existing target."""
    name = str(notebook_name or "").strip()
    if not _NAME_RE.fullmatch(name):
        return False, "Notebook creation failed: use 1-64 letters, numbers, spaces, '_' or '-' and start with a letter or number."

    root_value = configured_root
    if root_value is None:
        root_value = os.environ.get("PROJECT_CONTINUE_NOTEBOOK_CREATE_DIR", "")
    root = _safe_directory(root_value)
    if root is None:
        return False, "Notebook creation failed: configured destination is unavailable or unsafe."

    target = root / f"{name}.ipynb"
    document = _notebook_document(name)
    payload = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(payload) > MAX_NOTEBOOK_BYTES:
        return False, "Notebook creation failed: generated notebook exceeds the size limit."

    fd = None
    created = False
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(target, flags, 0o600)
        created = True
        with os.fdopen(fd, "wb") as stream:
            fd = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())

        info = target.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size != len(payload):
            raise OSError("created file failed regular-file/size verification")
        verified = target.read_bytes()
        parsed = json.loads(verified.decode("utf-8"))
        if parsed.get("nbformat") != 4 or not isinstance(parsed.get("cells"), list):
            raise ValueError("notebook JSON structure verification failed")
        if len(parsed["cells"]) != 2 or parsed["cells"][1].get("cell_type") != "code":
            raise ValueError("starter notebook cell verification failed")
    except FileExistsError:
        return False, "Notebook creation refused: a file with that name already exists; no file was overwritten."
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        if created:
            try:
                target.unlink()
            except OSError:
                pass
        return False, "Notebook creation failed: file write or JSON verification was unsuccessful."
    finally:
        if fd is not None:
            os.close(fd)

    digest = hashlib.sha256(payload).hexdigest()
    return True, (
        "Notebook created and JSON read-back verification passed. No code was executed.\n"
        f"File: {target.name}\n"
        f"Bytes: {len(payload)}\n"
        f"SHA-256: {digest}\n"
        "Existing files were not modified."
    )
