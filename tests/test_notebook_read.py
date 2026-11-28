import json

from scripts.notebook_read import read_notebook_redacted


def _payload():
    document = {
        "cells": [
            {
                "cell_type": "code",
                "id": "code-01",
                "metadata": {"api_key": "metadata-secret-value"},
                "execution_count": None,
                "outputs": [
                    {
                        "output_type": "stream",
                        "name": "stdout",
                        "text": ["Authorization: Bearer bearer-secret-value"],
                    }
                ],
                "source": [
                    "token = 'plain-secret-value'\n",
                    "github_token = 'ghp_" + "A" * 36 + "'\n",
                ],
            }
        ],
        "metadata": {"kernelspec": {"name": "python3"}, "password": "metadata-password"},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return json.dumps(document).encode("utf-8")


def test_notebook_read_redacts_secrets_in_source_metadata_and_outputs():
    payload = _payload()
    passed, document, errors = read_notebook_redacted(payload)
    assert passed, errors
    rendered = json.dumps(document)
    for secret in (
        "metadata-secret-value",
        "bearer-secret-value",
        "plain-secret-value",
        "ghp_" + "A" * 36,
        "metadata-password",
    ):
        assert secret not in rendered
    assert "[REDACTED]" in rendered
    assert "[REDACTED_GITHUB_TOKEN]" in rendered


def test_notebook_read_rejects_invalid_document_without_returning_content():
    passed, document, errors = read_notebook_redacted(b'{"token":"do-not-return"}')
    assert not passed
    assert document is None
    assert errors


def test_notebook_read_does_not_execute_code_or_change_payload():
    payload = _payload()
    original = bytes(payload)
    passed, document, _ = read_notebook_redacted(payload)
    assert passed
    assert payload == original
    assert document["cells"][0]["execution_count"] is None
