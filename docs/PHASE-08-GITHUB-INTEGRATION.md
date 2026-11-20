# Phase 08 — GitHub Integration

## Scope

A read-only GitHub REST integration for repository metadata, branch listing, recent commits, README/file verification, and open pull-request tracking. All client operations use HTTPS GET requests; this phase does not create branches, commits, issues, pull requests, or merge changes.

## Configuration

Copy `.env.example` to `.env` and configure:

```dotenv
GITHUB_REPOSITORY=owner/repository
GITHUB_TOKEN=
```

- Public repositories can be inspected anonymously, subject to GitHub's lower unauthenticated API rate limit.
- Private repositories require a fine-grained personal access token with read-only **Contents** and **Metadata** repository permissions.
- Keep the token in the untracked `.env` file or deployment secret store. Never commit or display it.
- The application settings expose only whether a token is configured, never the token value.

## Runtime

The Streamlit dashboard includes a **GitHub integration** panel. Select **Test GitHub connection** to perform a live check of repository metadata, up to 100 branches, five recent commits, the README file and up to 30 open pull requests.

The check is user-triggered; the app does not make repeated background API calls. Error messages are sanitized and do not include response bodies or credentials.

## Python usage

```python
from services.github_integration import GitHubIntegrationService

github = GitHubIntegrationService()
repository = github.repository_overview()
branches = github.branches()
commits = github.commits(branch=repository["default_branch"], per_page=5)
readme = github.verify_file("README.md", ref=repository["default_branch"])
pull_requests = github.pull_requests(state="open")
```

## Security and boundaries

- Read-only GET operations only.
- HTTPS, bounded request timeout, repository/path/state/page-size validation.
- Optional authentication supports public repositories; private repositories need a token.
- Tokens are excluded from settings representations and client representations.
- API and network errors are converted to safe messages.
- The integration is not a webhook receiver, CI deploy key, Git write client, or GitHub Actions control plane.

## Verification

Run:

```bash
python -m compileall -q .
python -m pytest -q
```

Automated tests use mocked HTTP responses and do not require a live token or network. The Streamlit **Test GitHub connection** action performs the live runtime check against the configured repository.
