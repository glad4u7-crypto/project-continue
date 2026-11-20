"""Validated application configuration loaded from environment variables."""

import os
from dataclasses import dataclass
from typing import Mapping

from dotenv import load_dotenv

from core.errors import ConfigurationError

load_dotenv()

_ALLOWED_ENVIRONMENTS = frozenset({"development", "test", "production"})
_ALLOWED_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


@dataclass(frozen=True)
class Settings:
    """Immutable, validated, non-secret application settings."""

    app_name: str = "Project Continue"
    app_env: str = "development"
    log_level: str = "INFO"
    github_repository: str = ""
    github_token_configured: bool = False

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        """Build settings from an explicit mapping or the process environment."""
        source = os.environ if environ is None else environ
        app_name = source.get("APP_NAME", "Project Continue").strip()
        app_env = source.get("APP_ENV", "development").strip().lower()
        log_level = source.get("LOG_LEVEL", "INFO").strip().upper()
        github_repository = source.get("GITHUB_REPOSITORY", "").strip()
        github_token_configured = bool(source.get("GITHUB_TOKEN", "").strip())

        if not app_name:
            raise ConfigurationError("APP_NAME must not be empty")
        if app_env not in _ALLOWED_ENVIRONMENTS:
            raise ConfigurationError("APP_ENV must be development, test, or production")
        if log_level not in _ALLOWED_LOG_LEVELS:
            raise ConfigurationError("LOG_LEVEL must be a standard Python logging level")
        if github_repository:
            parts = github_repository.split("/")
            if len(parts) != 2 or any(
                not part or part in {".", ".."}
                or not all(ch.isalnum() or ch in "_.-" for ch in part)
                for part in parts
            ):
                raise ConfigurationError("GITHUB_REPOSITORY must use owner/name format")
        return cls(
            app_name=app_name,
            app_env=app_env,
            log_level=log_level,
            github_repository=github_repository,
            github_token_configured=github_token_configured,
        )


def get_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Return a fresh validated settings object."""
    return Settings.from_env(environ)


settings = get_settings()
