"""Safe, redacted notebook read-back. Notebook code is never executed."""
from __future__ import annotations

import json
import re
from typing import Any

from core.security import redact_secrets
from scripts.notebook_validation import validate_notebook_payload

_SECRET_FIELD_RE = re.compile(
    r"(?i)(?:token|secret|password|credential|api[_-]?key|private[_-]?key)"
)


def _redact_value(value: Any, field_name: str = "") -> Any:
    """Recursively redact secret-labelled fields and credential-like strings."""
    if field_name and _SECRET_FIELD_RE.search(field_name):
        return "[REDACTED]"
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _redact_value(item, key if isinstance(key, str) else "")
            for key, item in value.items()
        }
    return value


def read_notebook_redacted(payload: bytes) -> tuple[bool, dict | None, tuple[str, ...]]:
    """Validate and return a sanitized notebook document without executing it.

    Invalid notebooks return no document. Source, outputs and metadata are all
    recursively sanitized before the caller can display or persist the result.
    """
    valid, errors = validate_notebook_payload(payload)
    if not valid:
        return False, None, errors
    try:
        document = json.loads(payload.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False, None, ("notebook could not be decoded safely",)
    sanitized = _redact_value(document)
    if not isinstance(sanitized, dict):
        return False, None, ("notebook root must be an object",)
    return True, sanitized, ()
