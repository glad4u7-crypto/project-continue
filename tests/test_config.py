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
