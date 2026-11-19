"""Cross-module acceptance tests for Phase 03 core architecture."""

import io

import pytest

from app.lifecycle import ApplicationLifecycle, LifecycleState
from config import get_settings
from core.errors import ConfigurationError, ValidationError
from core.logging import setup_logging
from core.validation import validate_identifier, validate_priority, validate_task_title


def test_core_components_work_together():
    settings = get_settings({
        "APP_NAME": "Project Continue Integration",
        "APP_ENV": "test",
        "LOG_LEVEL": "INFO",
    })
    stream = io.StringIO()
    logger = setup_logging("test.phase03.integration", settings.log_level, stream=stream)
    lifecycle = ApplicationLifecycle(
        on_start=lambda: logger.info("application started"),
        on_stop=lambda: logger.info("application stopped"),
    )

    assert validate_task_title(" Verify architecture ") == "Verify architecture"
    assert validate_identifier("PC-P03-S008") == "PC-P03-S008"
    assert validate_priority("critical") == "critical"
    assert lifecycle.start() is True
    assert lifecycle.state is LifecycleState.RUNNING
    assert lifecycle.stop() is True
    assert lifecycle.state is LifecycleState.STOPPED
    assert "application started" in stream.getvalue()
    assert "application stopped" in stream.getvalue()
    assert settings.app_env == "test"


def test_invalid_configuration_is_rejected_before_lifecycle_start():
    with pytest.raises(ConfigurationError):
        get_settings({"APP_ENV": "unknown"})
    lifecycle = ApplicationLifecycle()
    assert lifecycle.state is LifecycleState.CREATED


def test_invalid_domain_data_does_not_start_application():
    with pytest.raises(ValidationError):
        validate_task_title(" ")
    lifecycle = ApplicationLifecycle()
    assert lifecycle.state is LifecycleState.CREATED
