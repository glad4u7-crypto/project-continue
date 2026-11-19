"""Environment-backed configuration for Project Continue."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    """Application settings; secrets are optional and never hard-coded."""

    app_env: str = "development"
    github_token: str | None = None
    github_repo: str | None = None
    data_dir: Path = Path("data")
    log_level: str = "INFO"


def load_config(environ: Mapping[str, str] | None = None) -> AppConfig:
    """Load settings from .env/the process environment or an injected mapping."""
    if environ is None:
        load_dotenv()
        source: Mapping[str, str] = os.environ
    else:
        source = environ

    raw_data_dir = source.get("PROJECT_CONTINUE_DATA_DIR", "data").strip() or "data"
    raw_log_level = source.get("PROJECT_CONTINUE_LOG_LEVEL", "INFO").strip().upper() or "INFO"

    return AppConfig(
        app_env=source.get("PROJECT_CONTINUE_ENV", "development").strip() or "development",
        github_token=source.get("GITHUB_TOKEN") or None,
        github_repo=source.get("GITHUB_REPOSITORY") or None,
        data_dir=Path(raw_data_dir),
        log_level=raw_log_level,
    )
