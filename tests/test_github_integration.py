import pytest
import requests

from integrations.github_client import GitHubAPIError, GitHubClient
from services.github_integration import GitHubIntegrationService


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload if payload is not None else {"ok": True}
        self.status_code = status_code

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response=None, error=None):
        self.headers = {}
        self.response = response or FakeResponse()
        self.error = error
        self.calls = []

    def get(self, url, *, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        if self.error:
            raise self.error
        return self.response


def test_token_required_and_never_in_repr(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(ValueError, match="GITHUB_TOKEN"):
        GitHubClient()
    client = GitHubClient("secret-token")
    assert "secret-token" not in repr(client)
    assert "[REDACTED]" in repr(client)


def test_auth_headers_and_timeout():
    session = FakeSession()
    client = GitHubClient("abc123", timeout=9, session=session)
    assert session.headers["Authorization"] == "Bearer abc123"
    assert session.headers["Accept"] == "application/vnd.github+json"
    client.get_repository("owner/repo")
    assert session.calls[0][2] == 9


@pytest.mark.parametrize("timeout", [0, 121, True])
def test_timeout_validation(timeout):
    with pytest.raises(ValueError):
        GitHubClient("token", timeout=timeout)


def test_repository_and_branch_endpoints():
    session = FakeSession()
    client = GitHubClient("token", session=session)
    client.get_repository("owner/repo")
    client.list_branches("owner/repo", per_page=10)
    assert session.calls[0][0].endswith("/repos/owner/repo")
    assert session.calls[1][1] == {"per_page": 10}


def test_commit_file_and_pull_request_endpoints():
    session = FakeSession()
    client = GitHubClient("token", session=session)
    client.list_commits("owner/repo", branch="main")
    client.get_file("owner/repo", "docs/guide.md", ref="main")
    client.list_pull_requests("owner/repo", state="all")
    assert session.calls[0][1] == {"per_page": 30, "sha": "main"}
    assert "/contents/docs/guide.md" in session.calls[1][0]
    assert session.calls[1][1] == {"ref": "main"}
    assert session.calls[2][1] == {"state": "all", "per_page": 30}


def test_api_and_network_errors_are_sanitized():
    client = GitHubClient("secret", session=FakeSession(FakeResponse(status_code=403)))
    with pytest.raises(GitHubAPIError, match="HTTP 403") as exc:
        client.get_repository("owner/repo")
    assert "secret" not in str(exc.value)
    client = GitHubClient("secret", session=FakeSession(error=requests.Timeout("secret")))
    with pytest.raises(GitHubAPIError, match="Unable to reach"):
        client.get_repository("owner/repo")


@pytest.mark.parametrize("repository", ["", "owner", "../repo", "owner/repo/path"])
def test_invalid_repository(repository):
    with pytest.raises(ValueError):
        GitHubClient._repository(repository)


@pytest.mark.parametrize("path", ["", "/etc/passwd", "../secret", "docs/../secret"])
def test_invalid_file_path(path):
    client = GitHubClient("token", session=FakeSession())
    with pytest.raises(ValueError):
        client.get_file("owner/repo", path)


def test_invalid_state_and_page_size():
    client = GitHubClient("token", session=FakeSession())
    with pytest.raises(ValueError):
        client.list_pull_requests("owner/repo", state="merged")
    with pytest.raises(ValueError):
        client.list_branches("owner/repo", per_page=101)


def test_service_facade_uses_configured_repository():
    session = FakeSession()
    client = GitHubClient("token", session=session)
    service = GitHubIntegrationService(client, "owner/repo")
    service.repository_overview()
    assert session.calls[0][0].endswith("/repos/owner/repo")
