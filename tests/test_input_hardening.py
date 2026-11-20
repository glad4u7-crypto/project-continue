"""Boundary tests for user input and the read-only GitHub integration."""

import pytest

pytestmark = pytest.mark.unit

from core.errors import ValidationError
from core.validation import validate_dependencies, validate_project_name, validate_task_title
from integrations.github_client import GitHubClient


class FakeResponse:
    status_code = 200

    def json(self):
        return {"ok": True}


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.calls = []

    def get(self, url, *, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        return FakeResponse()


@pytest.mark.parametrize("value", ["Project\nInjected", "Task\x00Title", "Name\x7f"])
def test_single_line_names_reject_control_characters(value):
    with pytest.raises(ValidationError, match="control characters"):
        validate_project_name(value)


def test_task_title_rejects_tab_control_character():
    with pytest.raises(ValidationError, match="control characters"):
        validate_task_title("Deploy\tproduction")


@pytest.mark.parametrize("value", ["task-01", b"task-01", None, 42])
def test_dependencies_reject_scalar_or_non_iterable_inputs(value):
    with pytest.raises(ValidationError):
        validate_dependencies(value)


@pytest.mark.parametrize("repository", ["owner/naïve", "owner/repo?x=1", "owner/repo#tag"])
def test_github_repository_rejects_non_ascii_or_url_syntax(repository):
    with pytest.raises(ValueError):
        GitHubClient._repository(repository)


@pytest.mark.parametrize(
    "path",
    [
        "docs\\..\\secret",
        "docs//README.md",
        "docs/./README.md",
        "docs/README\n.md",
        "a" * 1025,
    ],
)
def test_github_file_paths_reject_ambiguous_or_unsafe_values(path):
    client = GitHubClient(session=FakeSession())
    with pytest.raises(ValueError):
        client.get_file("owner/repo", path)


@pytest.mark.parametrize("ref", ["../main", "main\n", "a//b", ".hidden", "release.lock"])
def test_github_refs_reject_invalid_branch_or_tag_names(ref):
    client = GitHubClient(session=FakeSession())
    with pytest.raises(ValueError):
        client.list_commits("owner/repo", branch=ref)


def test_github_refs_accept_normal_feature_branches():
    session = FakeSession()
    client = GitHubClient(session=session)
    client.list_commits("owner/repo", branch="feature/phase-10")
    assert session.calls[0][1] == {"per_page": 30, "sha": "feature/phase-10"}


def test_pull_request_state_requires_string():
    client = GitHubClient(session=FakeSession())
    with pytest.raises(ValueError):
        client.list_pull_requests("owner/repo", state=["open"])
