"""Small dependency-free validators for core project and task data."""

import re
import unicodedata
from collections.abc import Iterable

from core.errors import ValidationError

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_PRIORITIES = frozenset({"low", "medium", "high", "critical"})
_TASK_STATUSES = frozenset({"todo", "in_progress", "blocked", "done"})


def validate_text(value: str, *, field: str, max_length: int) -> str:
    """Return stripped non-empty single-line text within the requested length."""
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be text")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field} must not be empty")
    if len(normalized) > max_length:
        raise ValidationError(f"{field} exceeds {max_length} characters")
    if any(unicodedata.category(character) == "Cc" for character in normalized):
        raise ValidationError(f"{field} must not contain control characters")
    return normalized


def validate_project_name(value: str) -> str:
    return validate_text(value, field="Project name", max_length=100)


def validate_task_title(value: str) -> str:
    return validate_text(value, field="Task title", max_length=200)


def validate_identifier(value: str) -> str:
    normalized = validate_text(value, field="Identifier", max_length=64)
    if not _IDENTIFIER.fullmatch(normalized):
        raise ValidationError("Identifier contains unsupported characters")
    return normalized


def validate_priority(value: str) -> str:
    normalized = validate_text(value, field="Priority", max_length=20).lower()
    if normalized not in _PRIORITIES:
        raise ValidationError("Priority must be low, medium, high, or critical")
    return normalized


def validate_task_status(value: str) -> str:
    normalized = validate_text(value, field="Task status", max_length=20).lower()
    if normalized not in _TASK_STATUSES:
        raise ValidationError("Task status is not supported")
    return normalized


def validate_dependencies(
    dependencies: Iterable[str],
    *,
    task_id: str | None = None,
) -> tuple[str, ...]:
    """Validate dependency identifiers, rejecting scalar strings and self-links."""
    if isinstance(dependencies, (str, bytes)) or dependencies is None:
        raise ValidationError("Dependencies must be an iterable of identifiers")
    try:
        normalized = tuple(validate_identifier(item) for item in dependencies)
    except TypeError:
        raise ValidationError("Dependencies must be an iterable of identifiers") from None
    if len(set(normalized)) != len(normalized):
        raise ValidationError("Dependencies must not contain duplicates")
    if task_id is not None and validate_identifier(task_id) in normalized:
        raise ValidationError("A task cannot depend on itself")
    return normalized
