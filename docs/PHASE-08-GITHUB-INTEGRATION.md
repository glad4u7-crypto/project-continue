# Phase 08 — GitHub Integration

## Scope

A read-only GitHub REST integration for repository metadata, branches, commits,
file verification, and pull-request tracking. All calls use HTTPS GET requests;
this phase does not create branches, commits, pull requests, or merge changes.

## Checkpoints

| Checkpoint | Implementation |
| --- | --- |
| PC-P08-S001 GitHub API Connection | `GitHubClient` with bounded request timeout |
| PC-P08-S002 Token Security | `GITHUB_TOKEN` environment variable; redacted repr and sanitized errors |
| PC-P08-S003 Repository Inspection | `get_repository` |
| PC-P08-S004 Branch Inspection | `list_branches` |
| PC-P08-S005 Commit Inspection | `list_commits` |
| PC-P08-S006 File Verification | `get_file` |
| PC-P08-S007 Pull Request Tracking | `list_pull_requests` |
| PC-P08-S008 GitHub Integration Tests | Mock-based tests in `tests/test_github_integration.py` |

## Configuration

Set these values in the runtime environment or an untracked local `.env` file:

```dotenv
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_REPOSITORY=owner/repository
```

Never commit a real token. The repository's `.gitignore` excludes local environment
secrets. Use the minimum GitHub token permissions required to read repository data.

## Example

```python
from services.github_integration import GitHubIntegrationService

github = GitHubIntegrationService()
repository = github.repository_overview()
branches = github.branches()
commits = github.commits(branch="main")
readme = github.verify_file("README.md", ref="main")
pull_requests = github.pull_requests(state="open")
```

## Verification

Run:

```bash
pytest -q tests/test_github_integration.py
pytest -q
```

The tests mock HTTP calls and never require a real token or network access.
