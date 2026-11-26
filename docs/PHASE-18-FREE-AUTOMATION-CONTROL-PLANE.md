# Phase 18 — Free-Only Automation & Control Plane

## Objective

Provide a safe, auditable path for ChatGPT-assisted observation and approved operations across the Project Continue GitHub repository and its Streamlit dashboard, without paid services or uncontrolled production actions.

## Non-negotiable constraints

- Free-tier and open-source components only; no paid hosting, API, automation or monitoring dependency.
- Keep GitHub `main` protected by reviewable feature branches and pull requests.
- Preserve SQLite and the existing three Google Drive backup folders.
- Do not reboot the user's Colab runtime or stop/restart an existing Streamlit dashboard.
- Do not merge, deploy, change secrets, migrate a live database, or perform destructive recovery without explicit user approval.
- Never request passwords, tokens, signing keys or other secrets in chat.
- Keep the existing dashboard available; use isolated CI databases for tests.

## Verified starting point

- Repository: `glad4u7-crypto/project-continue`; canonical branch: `main`.
- Phase 17 U01–U04 are recorded in README as merged through PR #56; automated CI and Streamlit/Chromium browser acceptance are recorded as passing.
- The application currently has a read-only GitHub integration panel (`integrations/github_client.py`, `services/github_integration.py`, `ui/github_integration.py`).
- The app has a read-only self-check panel and a Streamlit health endpoint is used by the container health check.
- Production auth is fail-closed and requires host-managed secrets.
- SQLite remains the default runtime database. Streamlit Community Cloud local filesystem persistence is not guaranteed; it must not be treated as authoritative durable storage.
- Existing documentation explicitly distinguishes repository CI from live-host deployment and acceptance.

## Platform capability boundary

Streamlit Community Cloud does not provide this project with a supported general-purpose API to fetch platform process logs, restart the hosted app, or perform arbitrary deployment administration. The app can expose only application-level, sanitized diagnostics that it deliberately records. Platform logs and deployment controls remain in the provider's own interface unless a supported free integration is separately verified.

ChatGPT's existing GitHub connection can support repository-level inspection and permitted GitHub operations. A direct custom ChatGPT-to-Streamlit API action is not assumed: its availability on the user's current ChatGPT plan and connection surface must be verified before designing around it. Do not promise unattended, always-on control.

## Proposed architecture

1. **GitHub — source of truth for code and review:** feature branches, pull requests, CI, security checks and workflow evidence.
2. **GitHub Actions — free-tier bounded automation:** run repository tests, isolated browser acceptance, dependency/security checks and read-only diagnostics on disposable data. Enforce least privilege and workflow concurrency.
3. **Streamlit app — application-level health only:** expose sanitized status such as app version/commit, environment label, dependency readiness and database connectivity/integrity result without exposing paths, records, secrets or raw logs.
4. **Approval boundary:** all writes, deployments, restarts, migrations, secret changes and backup retention/recovery remain explicit human-approved operations. Read-only checks may be automated.
5. **Durable data:** retain the established Google Drive backup strategy; never rely on Community Cloud's local filesystem for authoritative SQLite persistence.

## Delivery checkpoints

- **P18-S001 — Capability and permission audit:** confirm which GitHub operations are available through the linked connection, which Streamlit controls are genuinely exposed, and which operations require a user in the provider UI.
- **P18-S002 — Threat model and operation matrix:** classify every action as read-only, reversible write, or destructive; define authentication, authorization, audit and approval rules.
- **P18-S003 — Read-only status contract:** define a minimal sanitized health/status schema and tests; no raw log or personal-data exposure.
- **P18-S004 — GitHub Actions control workflows:** add least-privilege, manually approved, free-tier workflows for CI/status tasks only; no production secrets or deployment by default.
- **P18-S005 — ChatGPT workflow verification:** test the actual available GitHub connection actions and determine whether a supported direct API action exists on the user's plan. If not, document a safe manual approval bridge rather than claiming direct control.
- **P18-S006 — Acceptance and handoff:** run isolated tests, document free-tier limits and provide a single operator runbook. Live-host acceptance remains separate.

## Initial acceptance criteria

- No paid dependency is introduced.
- No existing runtime, dashboard, database or backup folder is stopped, restarted, deleted or modified by this phase.
- Read-only checks reveal no secret, database path, user/project content or raw sensitive log.
- Every write-capable workflow is disabled by default or requires explicit approval.
- CI evidence is tied to the exact commit SHA and uses disposable data.
- The documentation clearly distinguishes GitHub repository access, in-app diagnostics, provider-platform logs, and actual deployment controls.

## Current status

Phase 18 has been opened on `feature/phase-18-free-control-plane`. This initial document is a design and verification plan only; no application code, production configuration, secrets, database, dashboard or deployment has been changed.
