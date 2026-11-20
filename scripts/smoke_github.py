"""Live, anonymous read-only smoke test for the configured public GitHub repository."""
from __future__ import annotations

import os
import sys

from services.github_integration import GitHubIntegrationService


def main() -> int:
    repository_name = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not repository_name:
        print("FAIL: GITHUB_REPOSITORY is not configured")
        return 1

    try:
        github = GitHubIntegrationService(repository=repository_name)
        repository = github.repository_overview()
        if repository.get("full_name", "").lower() != repository_name.lower():
            raise RuntimeError("GitHub returned a different repository")
        print("PASS: repository metadata")

        branches = github.branches(per_page=5)
        if not isinstance(branches, list):
            raise RuntimeError("Branch response was not a list")
        print(f"PASS: branch listing ({len(branches)} returned)")

        default_branch = repository.get("default_branch")
        commits = github.commits(branch=default_branch, per_page=3)
        if not isinstance(commits, list):
            raise RuntimeError("Commit response was not a list")
        print(f"PASS: recent commits ({len(commits)} returned)")

        readme = github.verify_file("README.md", ref=default_branch)
        if readme.get("name") != "README.md":
            raise RuntimeError("README verification returned an unexpected file")
        print("PASS: README file verification")

        pull_requests = github.pull_requests(state="open", per_page=5)
        if not isinstance(pull_requests, list):
            raise RuntimeError("Pull request response was not a list")
        print(f"PASS: pull request listing ({len(pull_requests)} returned)")
    except Exception as exc:
        # GitHubClient exceptions are already sanitized; never print headers or token data.
        print(f"FAIL: live GitHub API check ({type(exc).__name__}): {exc}")
        return 1

    print("LIVE GITHUB INTEGRATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
