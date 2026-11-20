"""Small, dependency-free helpers for redacting common credential formats."""

import re

_PATTERNS = (
    (re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"(?i)\b(token|api[_-]?key|password|secret)\s*[:=]\s*([^\s,;&]+)"), r"\1=[REDACTED]"),
)


def redact_secrets(value: object) -> str:
    """Return text with common bearer tokens and key/value credentials masked."""
    text = str(value)
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text
