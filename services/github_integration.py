"""Application-facing read-only GitHub integration service."""
from __future__ import annotations

import os
from typing import Any

from integrations.github_client import GitHubClient


class GitHubIntegrationService:
    """Read-only repository dashboard data backed by the GitHub REST API."""

    def __init__(self, client: GitHubClient | None = None,
                 repository: str | None = None) -> None:
        self.client = client or GitHubClient()
        self.repository = repository if repository is not None else os.getenv("GITHUB_REPOSITORY", "")
        self.repository = self.client._repository(self.repository.strip())

    @property
    def authenticated(self) -> bool:
        return self.client.authenticated

    def repository_overview(self) -> dict[str, Any]:
        return self.client.get_repository(self.repository)

    def branches(self, *, per_page: int = 30) -> list[dict[str, Any]]:
        return self.client.list_branches(self.repository, per_page=per_page)

    def commits(self, *, branch: str | None = None, per_page: int = 30) -> list[dict[str, Any]]:
        return self.client.list_commits(self.repository, branch=branch, per_page=per_page)

    def verify_file(self, path: str, *, ref: str | None = None) -> dict[str, Any]:
        return self.client.get_file(self.repository, path, ref=ref)

    def pull_requests(self, *, state: str = "open", per_page: int = 30) -> list[dict[str, Any]]:
        return self.client.list_pull_requests(self.repository, state=state, per_page=per_page)
