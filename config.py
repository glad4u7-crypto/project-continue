"""Validated application configuration loaded from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv

from core.errors import ConfigurationError

load_dotenv()

_ALLOWED_ENVIRONMENTS = frozenset({"development", "test", "production"})
_ALLOWED_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
_ALLOWED_DATABASE_BACKENDS = frozenset({"sqlite", "postgresql"})
_DEFAULT_DATABASE_PATH = ".data/project_continue.sqlite3"


@dataclass(frozen=True)
class Settings:
    """Immutable, validated, non-secret application settings."""

    app_name: str = "Project Continue"
    app_env: str = "development"
    log_level: str = "INFO"
    github_repository: str = ""
    github_token_configured: bool = False
    session_signing_key_configured: bool = False
    database_path: str = _DEFAULT_DATABASE_PATH
    database_backend: str = "sqlite"
    postgres_dsn: str = ""

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        """Build settings from an explicit mapping or the process environment."""
        source = os.environ if environ is None else environ
        app_name = source.get("APP_NAME", "Project Continue").strip()
        app_env = source.get("APP_ENV", "development").strip().lower()
        log_level = source.get("LOG_LEVEL", "INFO").strip().upper()
        github_repository = source.get("GITHUB_REPOSITORY", "").strip()
        github_token_configured = bool(source.get("GITHUB_TOKEN", "").strip())
        session_signing_key = source.get("SESSION_SIGNING_KEY", "").strip()
        raw_database_path = source.get("PROJECT_CONTINUE_DB", _DEFAULT_DATABASE_PATH)
        if not isinstance(raw_database_path, str):
            raise ConfigurationError("PROJECT_CONTINUE_DB must be a filesystem path")
        database_path = raw_database_path.strip()
        expanded_database_path = Path(database_path).expanduser()
        database_backend = source.get("PROJECT_CONTINUE_DB_BACKEND", "sqlite").strip().lower()
        postgres_dsn = source.get("PROJECT_CONTINUE_POSTGRES_DSN", "").strip()

        if not app_name:
            raise ConfigurationError("APP_NAME must not be empty")
        if len(app_name) > 100:
            raise ConfigurationError("APP_NAME must be 100 characters or fewer")
        if app_env not in _ALLOWED_ENVIRONMENTS:
            raise ConfigurationError("APP_ENV must be development, test, or production")
        if log_level not in _ALLOWED_LOG_LEVELS:
            raise ConfigurationError("LOG_LEVEL must be a standard Python logging level")
        if database_backend not in _ALLOWED_DATABASE_BACKENDS:
            raise ConfigurationError("PROJECT_CONTINUE_DB_BACKEND must be sqlite or postgresql")
        if not database_path or "\x00" in database_path:
            raise ConfigurationError("PROJECT_CONTINUE_DB must be a valid non-empty path")
        if database_backend == "postgresql" and not postgres_dsn:
            raise ConfigurationError(
                "PROJECT_CONTINUE_POSTGRES_DSN is required when PostgreSQL is selected"
            )
        if app_env == "production":
            if log_level == "DEBUG":
                raise ConfigurationError("LOG_LEVEL=DEBUG is not allowed in production")
            if database_backend == "sqlite" and not expanded_database_path.is_absolute():
                raise ConfigurationError(
                    "PROJECT_CONTINUE_DB must be an absolute path in production"
                )
            if len(session_signing_key.encode("utf-8")) < 32:
                raise ConfigurationError("SESSION_SIGNING_KEY must contain at least 32 bytes in production")
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
            session_signing_key_configured=len(session_signing_key.encode("utf-8")) >= 32,
            database_path=str(expanded_database_path),
            database_backend=database_backend,
            postgres_dsn=postgres_dsn,
        )


def get_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Return a fresh validated settings object."""
    return Settings.from_env(environ)


settings = get_settings()
