import json
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from scripts.colab_dashboard_status import (
    check_local_streamlit,
    publish_commit_status,
)


def _response(status):
    response = Mock()
    response.status = status
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    return response


def test_local_streamlit_health_passes_on_http_200():
    with patch("scripts.colab_dashboard_status.build_opener") as build_opener:
        build_opener.return_value.open.return_value = _response(200)
        passed, detail = check_local_streamlit()
    assert passed is True
    assert detail == "Local Streamlit health endpoint returned HTTP 200"
    request = build_opener.return_value.open.call_args.args[0]
    assert request.full_url == "http://127.0.0.1:8501/_stcore/health"


def test_local_streamlit_health_rejects_redirect():
    with patch("scripts.colab_dashboard_status.build_opener") as build_opener:
        build_opener.return_value.open.side_effect = HTTPError(
            "http://127.0.0.1:8501/_stcore/health", 302, "redirect", {}, None
        )
        passed, detail = check_local_streamlit()
    assert passed is False
    assert detail == "Local Streamlit health endpoint returned HTTP 302"


def test_commit_status_uses_limited_context_and_exact_sha():
    sha = "a" * 40
    with patch("scripts.colab_dashboard_status.build_opener") as build_opener:
        build_opener.return_value.open.return_value = _response(201)
        assert publish_commit_status("secret-token", sha, True) is True
    request = build_opener.return_value.open.call_args.args[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert request.method == "POST"
    assert request.full_url.endswith(f"/statuses/{sha}")
    assert payload == {
        "state": "success",
        "context": "project-continue/colab-dashboard-health",
        "description": "Colab Streamlit health endpoint returned HTTP 200",
    }
    assert request.get_header("Authorization") == "Bearer secret-token"


def test_commit_status_rejects_invalid_sha_without_network_call():
    with patch("scripts.colab_dashboard_status.build_opener") as build_opener:
        assert publish_commit_status("secret-token", "not-a-sha", True) is False
        build_opener.assert_not_called()
