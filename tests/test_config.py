from dataclasses import FrozenInstanceError

import pytest

pytestmark = pytest.mark.unit

from config import Settings, settings
from core.errors import ConfigurationError


def test_settings_exist():
    assert settings is not None


def test_settings_have_valid_values():
    assert isinstance(settings.app_name, str)
    assert isinstance(settings.app_env, str)
    assert isinstance(settings.log_level, str)
    assert isinstance(settings.github_repository, str)
    assert isinstance(settings.github_token_configured, bool)
    assert isinstance(settings.session_signing_key_configured, bool)
    assert isinstance(settings.database_path, str)
    assert settings.app_name != ""


def test_settings_are_immutable():
    with pytest.raises(FrozenInstanceError):
        settings.app_name = "Changed Name"


def test_github_settings_are_loaded_without_exposing_token():
    configured = Settings.from_env({
        "APP_NAME": "Test",
        "APP_ENV": "test",
        "LOG_LEVEL": "DEBUG",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_TOKEN": "private-secret",
    })
    assert configured.github_repository == "owner/repo"
    assert configured.github_token_configured is True
    assert "private-secret" not in repr(configured)


@pytest.mark.parametrize("repository", ["owner", "../repo", "owner/repo/path", "owner/.."])
def test_invalid_github_repository_is_rejected(repository):
    with pytest.raises(ConfigurationError):
        Settings.from_env({"GITHUB_REPOSITORY": repository})


def test_production_requires_absolute_database_path():
    with pytest.raises(ConfigurationError, match="absolute path"):
        Settings.from_env({"APP_ENV": "production"})


def test_production_accepts_absolute_database_path():
    configured = Settings.from_env({
        "APP_ENV": "production",
        "PROJECT_CONTINUE_DB": "/var/lib/project-continue/data.sqlite3",
        "LOG_LEVEL": "INFO",
        "SESSION_SIGNING_KEY": "s" * 48,
    })
    assert configured.database_path == "/var/lib/project-continue/data.sqlite3"


def test_debug_logging_is_rejected_in_production():
    with pytest.raises(ConfigurationError, match="DEBUG"):
        Settings.from_env({
            "APP_ENV": "production",
            "PROJECT_CONTINUE_DB": "/var/lib/project-continue/data.sqlite3",
            "LOG_LEVEL": "DEBUG",
            "SESSION_SIGNING_KEY": "s" * 48,
        })


@pytest.mark.parametrize("path", ["", "   ", "bad\x00path"])
def test_invalid_database_path_is_rejected(path):
    with pytest.raises(ConfigurationError, match="PROJECT_CONTINUE_DB"):
        Settings.from_env({"PROJECT_CONTINUE_DB": path})


def test_database_path_defaults_to_local_data_directory():
    configured = Settings.from_env({"APP_ENV": "development"})
    assert configured.database_path.endswith(".data/project_continue.sqlite3")


def test_app_name_length_is_bounded():
    with pytest.raises(ConfigurationError, match="100 characters"):
        Settings.from_env({"APP_NAME": "x" * 101})
