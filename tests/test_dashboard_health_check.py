from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from scripts.check_dashboard_health import check_dashboard_health, main


def test_health_probe_accepts_https_and_returns_pass():
    response = Mock()
    response.status = 200
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    with patch("scripts.check_dashboard_health.build_opener") as build_opener:
        build_opener.return_value.open.return_value = response
        passed, detail = check_dashboard_health("https://dashboard.example")
    assert passed is True
    assert detail == "Streamlit health endpoint returned HTTP 200"
    request = build_opener.return_value.open.call_args.args[0]
    assert request.full_url == "https://dashboard.example/_stcore/health"


def test_health_probe_rejects_non_https_and_credentials():
    assert check_dashboard_health("http://dashboard.example")[0] is False
    assert check_dashboard_health("https://user:pass@dashboard.example")[0] is False
    assert check_dashboard_health("https://dashboard.example/?token=secret")[0] is False


def test_health_probe_does_not_follow_redirects():
    with patch("scripts.check_dashboard_health.build_opener") as build_opener:
        build_opener.return_value.open.side_effect = HTTPError(
            "https://dashboard.example/_stcore/health", 302, "redirect", {}, None
        )
        passed, detail = check_dashboard_health("https://dashboard.example")
    assert passed is False
    assert detail == "Streamlit health endpoint returned HTTP 302"


def test_health_probe_sanitizes_connection_errors():
    with patch("scripts.check_dashboard_health.build_opener") as build_opener:
        build_opener.return_value.open.side_effect = URLError("private network detail")
        passed, detail = check_dashboard_health("https://dashboard.example")
    assert passed is False
    assert detail == "Streamlit health endpoint could not be reached"


def test_cli_skips_when_dashboard_url_is_not_configured(capsys):
    assert main(["--url", ""]) == 0
    assert capsys.readouterr().out.strip() == "SKIP: STREAMLIT_APP_URL is not configured"
