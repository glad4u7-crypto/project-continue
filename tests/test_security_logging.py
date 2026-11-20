"""Security regression tests for application log redaction."""

from io import StringIO
import uuid

import pytest

pytestmark = pytest.mark.unit

from core.errors import handle_application_error
from core.logging import setup_logging
from core.security import redact_secrets


def test_common_github_tokens_and_bearer_headers_are_redacted():
    secrets = [
        "ghp_" + "A" * 36,
        "github_pat_" + "B" * 30,
        "Bearer " + "C" * 32,
    ]
    for secret in secrets:
        redacted = redact_secrets(f"Authorization: {secret}")
        assert secret not in redacted
        assert "REDACTED" in redacted


def test_log_handler_redacts_formatted_messages():
    output = StringIO()
    logger = setup_logging(f"project_continue.security.{uuid.uuid4().hex}", stream=output)
    secret = "ghp_" + "D" * 36

    logger.warning("GitHub request failed token=%s", secret)

    rendered = output.getvalue()
    assert secret not in rendered
    assert "[REDACTED" in rendered


def test_application_error_does_not_log_exception_message_or_context_secret():
    output = StringIO()
    logger = setup_logging(f"project_continue.error.{uuid.uuid4().hex}", stream=output)
    secret = "github_pat_" + "E" * 30

    result = handle_application_error(
        RuntimeError(f"upstream returned {secret}"),
        logger,
        context=f"Authorization: Bearer {secret}",
    )

    rendered = output.getvalue()
    assert result == 1
    assert secret not in rendered
    assert "RuntimeError" in rendered
    assert "upstream returned" not in rendered
    assert "[REDACTED]" in rendered
