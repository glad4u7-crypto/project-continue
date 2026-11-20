"""Streamlit panel for live, read-only GitHub repository inspection."""
from __future__ import annotations

import streamlit as st

from config import settings
from integrations.github_client import GitHubAPIError
from services.github_integration import GitHubIntegrationService


def render_github_integration() -> None:
    """Render a user-triggered live connection check and repository overview."""
    st.divider()
    st.header("GitHub integration")
    st.caption("Read-only connection · repository, branches, commits, files and pull requests")

    repository = settings.github_repository
    if not repository:
        st.warning("GitHub repository is not configured. Set GITHUB_REPOSITORY in your .env file.")
        return

    token_state = "Token configured" if settings.github_token_configured else "Public/anonymous access"
    st.caption(f"Repository: {repository} · Authentication: {token_state}")
    if not settings.github_token_configured:
        st.info(
            "Public repositories can be checked without a token. For private repositories, "
            "add GITHUB_TOKEN to the local .env file with read-only repository Contents and Metadata access."
        )

    if not st.button("Test GitHub connection", type="primary", key="github_connection_test"):
        return

    try:
        service = GitHubIntegrationService(repository=repository)
        with st.spinner("Contacting GitHub and reading repository metadata…"):
            repo = service.repository_overview()
            branches = service.branches(per_page=100)
            commits = service.commits(branch=repo.get("default_branch"), per_page=5)
            pull_requests = service.pull_requests(state="open", per_page=30)
            readme = service.verify_file("README.md", ref=repo.get("default_branch"))
    except (GitHubAPIError, ValueError):
        st.error(
            "GitHub connection could not be verified. Check the repository name, token permissions, "
            "network access and GitHub API rate limit."
        )
        return

    st.success("Live GitHub connection verified.")
    a, b, c, d = st.columns(4)
    a.metric("Visibility", "Private" if repo.get("private") else "Public")
    b.metric("Default branch", repo.get("default_branch", "—"))
    c.metric("Branches", len(branches))
    d.metric("Open pull requests", len(pull_requests))
    st.markdown(f'**Repository:** [{repo.get("full_name", repository)}]({repo.get("html_url", "https://github.com")})')
    st.caption(f"README verified · {readme.get('name', 'README.md')} · {readme.get('size', 0)} bytes")

    with st.expander("Branches", expanded=False):
        for branch in branches:
            st.write(f'• {branch.get("name", "unknown")} · {branch.get("commit", {}).get("sha", "")[:8]}')

    with st.expander("Recent commits", expanded=False):
        for commit in commits:
            details = commit.get("commit", {})
            message = details.get("message", "No commit message").splitlines()[0]
            sha = commit.get("sha", "")[:8]
            st.write(f"• {sha} — {message}")

    with st.expander("Open pull requests", expanded=False):
        if not pull_requests:
            st.caption("No open pull requests.")
        for pull in pull_requests:
            st.write(f'• #{pull.get("number")} {pull.get("title", "Untitled")} ({pull.get("state", "unknown")})')
