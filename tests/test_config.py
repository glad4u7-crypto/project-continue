from dataclasses import FrozenInstanceError

import pytest

from config import settings


def test_settings_exist():
    assert settings is not None


def test_settings_have_valid_values():
    assert isinstance(settings.app_name, str)
    assert isinstance(settings.app_env, str)
    assert isinstance(settings.log_level, str)
    assert settings.app_name != ""


def test_settings_are_immutable():
    with pytest.raises(FrozenInstanceError):
        settings.app_name = "Changed Name"
