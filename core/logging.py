"""Consistent, idempotent application logging configuration."""

import logging
import sys
from typing import TextIO

from core.errors import ConfigurationError

_HANDLER_MARKER = "_project_continue_handler"


def setup_logging(
    name: str = "project_continue",
    level: str = "INFO",
    *,
    stream: TextIO | None = None,
) -> logging.Logger:
    """Configure a named logger once without changing global root logging."""
    normalized_level = level.strip().upper()
    numeric_level = logging.getLevelName(normalized_level)
    if not isinstance(numeric_level, int):
        raise ConfigurationError("Unsupported logging level")

    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    logger.propagate = False
    if not any(getattr(handler, _HANDLER_MARKER, False) for handler in logger.handlers):
        handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        setattr(handler, _HANDLER_MARKER, True)
        logger.addHandler(handler)
    for handler in logger.handlers:
        if getattr(handler, _HANDLER_MARKER, False):
            handler.setLevel(numeric_level)
    return logger
