"""Shared, explicitly selected Streamlit database resources.

SQLite remains the default. PostgreSQL is selected only by explicit validated
configuration; no migration or production switch is performed here.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import get_settings
from database import Database, ProjectRepository
from database.postgres_connection import PostgresDatabase
from database.postgres_repository import PostgresProjectRepository
from database.contracts import ProjectRepositoryProtocol


@st.cache_resource(show_spinner=False)
def _repository_for_path(database_path: str) -> ProjectRepository:
    """Create and initialize exactly one SQLite repository per path."""
    database = Database(database_path)
    repository = ProjectRepository(database)
    repository.initialize()
    return repository


@st.cache_resource(show_spinner=False)
def _postgres_repository_for_dsn(dsn: str) -> PostgresProjectRepository:
    """Create and initialize exactly one PostgreSQL repository per DSN."""
    database = PostgresDatabase(dsn)
    repository = PostgresProjectRepository(database)
    repository.initialize()
    return repository


def get_project_repository(
    database_path: str | Path | None = None,
    *,
    backend: str | None = None,
    postgres_dsn: str | None = None,
) -> ProjectRepositoryProtocol:
    """Return the cached repository selected by explicit arguments or settings.

    An explicit backend override is intended for isolated tests and controlled
    deployments. SQLite remains the default and existing callers are unchanged.
    """
    settings = get_settings()
    selected_backend = (backend or settings.database_backend).strip().lower()
    if selected_backend == "sqlite":
        path = str(database_path if database_path is not None else settings.database_path)
        return _repository_for_path(path)
    if selected_backend == "postgresql":
        dsn = postgres_dsn if postgres_dsn is not None else settings.postgres_dsn
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("PostgreSQL backend requires PROJECT_CONTINUE_POSTGRES_DSN")
        return _postgres_repository_for_dsn(dsn.strip())
    raise ValueError("Database backend must be sqlite or postgresql")
