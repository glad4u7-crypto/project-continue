"""Read-only GitHub REST client with conservative secret handling."""
from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import quote

import requests


class GitHubAPIError(RuntimeError):
    """Safe, user-facing GitHub API error."""


class GitHubClient:
    API_ROOT = "https://api.github.com"
    DEFAULT_TIMEOUT = 15

    def __init__(self, token: str | None = None, *, timeout: int = DEFAULT_TIMEOUT,
                 session: requests.Session | None = None) -> None:
        token = token if token is not None else os.getenv("GITHUB_TOKEN")
        if not token or not token.strip():
            raise ValueError("GITHUB_TOKEN is required")
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout < 1 or timeout > 120:
            raise ValueError("timeout must be an integer between 1 and 120 seconds")
        self.__token = token.strip()
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "project-continue-phase-08",
        })

    def __repr__(self) -> str:
        return f"{type(self).__name__}(token='[REDACTED]', timeout={self.timeout})"

    @staticmethod
    def _repository(repository: str) -> str:
        if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("repository must use owner/name format")
        return repository

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        try:
            response = self.session.get(f"{self.API_ROOT}{path}", params=params, timeout=self.timeout)
            if response.status_code >= 400:
                raise GitHubAPIError(f"GitHub API request failed (HTTP {response.status_code})")
            return response.json()
        except GitHubAPIError:
            raise
        except requests.RequestException:
            raise GitHubAPIError("Unable to reach GitHub API") from None
        except ValueError:
            raise GitHubAPIError("GitHub API returned an invalid response") from None

    def get_repository(self, repository: str) -> dict[str, Any]:
        repo = self._repository(repository)
        return self._get(f"/repos/{repo}")

    def list_branches(self, repository: str, *, per_page: int = 30) -> list[dict[str, Any]]:
        repo = self._repository(repository)
        self._validate_page_size(per_page)
        return self._get(f"/repos/{repo}/branches", params={"per_page": per_page})

    def list_commits(self, repository: str, *, branch: str | None = None,
                     per_page: int = 30) -> list[dict[str, Any]]:
        repo = self._repository(repository)
        self._validate_page_size(per_page)
        params: dict[str, Any] = {"per_page": per_page}
        if branch:
            params["sha"] = branch
        return self._get(f"/repos/{repo}/commits", params=params)

    def get_file(self, repository: str, path: str, *, ref: str | None = None) -> dict[str, Any]:
        repo = self._repository(repository)
        if not isinstance(path, str) or not path.strip() or path.startswith("/") or ".." in path.split("/"):
            raise ValueError("path must be a safe repository-relative file path")
        encoded = quote(path, safe="/")
        params = {"ref": ref} if ref else None
        return self._get(f"/repos/{repo}/contents/{encoded}", params=params)

    def list_pull_requests(self, repository: str, *, state: str = "open",
                           per_page: int = 30) -> list[dict[str, Any]]:
        repo = self._repository(repository)
        if state not in {"open", "closed", "all"}:
            raise ValueError("state must be open, closed, or all")
        self._validate_page_size(per_page)
        return self._get(f"/repos/{repo}/pulls", params={"state": state, "per_page": per_page})

    @staticmethod
    def _validate_page_size(per_page: int) -> None:
        if isinstance(per_page, bool) or not isinstance(per_page, int) or not 1 <= per_page <= 100:
            raise ValueError("per_page must be an integer between 1 and 100")
