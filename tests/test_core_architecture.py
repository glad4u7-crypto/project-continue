import io
import logging
from dataclasses import FrozenInstanceError

import pytest

from app.lifecycle import ApplicationLifecycle, LifecycleState
from config import Settings, get_settings
from core.errors import ConfigurationError, LifecycleError, ValidationError, handle_application_error
from core.logging import setup_logging
from core.validation import (
    validate_dependencies,
    validate_identifier,
    validate_priority,
    validate_project_name,
    validate_task_status,
    validate_task_title,
)


def test_configuration_defaults_and_normalization():
    assert get_settings({}) == Settings()
    assert get_settings({"APP_NAME": "  Demo  ", "APP_ENV": "TEST", "LOG_LEVEL": "debug"}) == Settings(
        app_name="Demo", app_env="test", log_level="DEBUG"
    )


@pytest.mark.parametrize("values", [
    {"APP_NAME": " "},
    {"APP_ENV": "staging"},
    {"LOG_LEVEL": "VERBOSE"},
])
def test_configuration_rejects_invalid_values(values):
    with pytest.raises(ConfigurationError):
        get_settings(values)


def test_settings_are_immutable():
    value = get_settings({})
    with pytest.raises(FrozenInstanceError):
        value.app_name = "mutated"


def test_logging_setup_is_idempotent_and_uses_requested_level():
    stream = io.StringIO()
    logger = setup_logging("test.project_continue", "DEBUG", stream=stream)
    first_count = len(logger.handlers)
    same_logger = setup_logging("test.project_continue", "WARNING", stream=stream)
    assert same_logger is logger
    assert len(logger.handlers) == first_count == 1
    assert logger.level == logging.WARNING
    logger.warning("safe event")
    assert "safe event" in stream.getvalue()


def test_application_error_handler_does_not_echo_exception_message():
    stream = io.StringIO()
    logger = logging.getLogger("test.error.handler")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.ERROR)
    logger.addHandler(logging.StreamHandler(stream))
    assert handle_application_error(RuntimeError("sensitive detail"), logger) == 1
    assert "RuntimeError" in stream.getvalue()
    assert "sensitive detail" not in stream.getvalue()


def test_validation_normalizes_valid_values():
    assert validate_project_name("  Demo Project ") == "Demo Project"
    assert validate_task_title("  Ship feature ") == "Ship feature"
    assert validate_identifier("task-01") == "task-01"
    assert validate_priority("HIGH") == "high"
    assert validate_task_status("In_Progress") == "in_progress"
    assert validate_dependencies(["task-01", "task-02"]) == ("task-01", "task-02")


@pytest.mark.parametrize("call", [
    lambda: validate_project_name(" "),
    lambda: validate_task_title("x" * 201),
    lambda: validate_identifier("../secret"),
    lambda: validate_priority("urgent"),
    lambda: validate_task_status("finished"),
    lambda: validate_dependencies(["task-1", "task-1"]),
    lambda: validate_dependencies(["task-1"], task_id="task-1"),
])
def test_validation_rejects_invalid_values(call):
    with pytest.raises(ValidationError):
        call()


def test_lifecycle_transitions_and_hooks():
    events = []
    lifecycle = ApplicationLifecycle(
        on_start=lambda: events.append("start"),
        on_stop=lambda: events.append("stop"),
    )
    assert lifecycle.state is LifecycleState.CREATED
    assert lifecycle.start() is True
    assert lifecycle.start() is False
    assert lifecycle.state is LifecycleState.RUNNING
    assert lifecycle.stop() is True
    assert lifecycle.stop() is False
    assert lifecycle.state is LifecycleState.STOPPED
    assert events == ["start", "stop"]


def test_lifecycle_marks_startup_failure():
    def fail():
        raise RuntimeError("failure")
    lifecycle = ApplicationLifecycle(on_start=fail)
    with pytest.raises(LifecycleError):
        lifecycle.start()
    assert lifecycle.state is LifecycleState.FAILED


def test_lifecycle_rejects_restart_after_stop():
    lifecycle = ApplicationLifecycle()
    lifecycle.start()
    lifecycle.stop()
    with pytest.raises(LifecycleError):
        lifecycle.start()
