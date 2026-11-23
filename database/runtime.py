"""Shared Streamlit database and repository resources.

The cached repository owns the Database instance for the lifetime of the
Streamlit resource cache. UI render functions must borrow it and must never
close it themselves.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import get_settings
from database import Database, ProjectRepository


@st.cache_resource(show_spinner=False)
def _repository_for_path(database_path: str) -> ProjectRepository:
    """Create and initialize exactly one repository per database path."""
    database = Database(database_path)
    repository = ProjectRepository(database)
    repository.initialize()
    return repository


def get_project_repository(
    database_path: str | Path | None = None,
) -> ProjectRepository:
    """Return the shared initialized repository for the configured database."""
    path = str(database_path if database_path is not None else get_settings().database_path)
    return _repository_for_path(path)
