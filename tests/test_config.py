"""Tests for environment-backed configuration."""
from config import load_config


def test_defaults_are_safe():
    config = load_config({})
    assert config.app_env == "development"
    assert config.github_token is None
    assert config.github_repo is None
    assert str(config.data_dir) == "data"


def test_configuration_can_be_injected_without_process_secrets():
    config = load_config({
        "PROJECT_CONTINUE_ENV": "test",
        "GITHUB_TOKEN": "test-token",
        "GITHUB_REPOSITORY": "owner/repo",
        "PROJECT_CONTINUE_DATA_DIR": "tmp-data",
        "PROJECT_CONTINUE_LOG_LEVEL": "debug",
    })
    assert config.app_env == "test"
    assert config.github_token == "test-token"
    assert config.github_repo == "owner/repo"
    assert str(config.data_dir) == "tmp-data"
    assert config.log_level == "DEBUG"
