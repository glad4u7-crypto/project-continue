"""Application-wide exception types and safe error handling."""

import logging


class ProjectContinueError(Exception):
    """Base class for expected application errors."""


class ConfigurationError(ProjectContinueError, ValueError):
    """Raised when application configuration is invalid."""


class ValidationError(ProjectContinueError, ValueError):
    """Raised when user or domain input is invalid."""


class LifecycleError(ProjectContinueError, RuntimeError):
    """Raised when an application lifecycle transition is invalid."""


def handle_application_error(
    error: Exception,
    logger: logging.Logger,
    *,
    context: str = "Application operation failed",
) -> int:
    """Log an application error without exposing sensitive details to users."""
    logger.error("%s: %s", context, error.__class__.__name__)
    return 1
