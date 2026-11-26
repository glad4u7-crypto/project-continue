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
- The application has a read-only GitHub integration panel and an administrator-triggered, read-only Automated self-check.
- Streamlit's built-in `/_stcore/health` endpoint provides server-level HTTP health.
- Production auth is fail-closed and requires host-managed secrets.
- SQLite remains the default runtime database. Streamlit Community Cloud local filesystem persistence is not guaranteed; it must not be treated as authoritative durable storage.

## Platform capability boundary

Streamlit Community Cloud does not provide this project with a supported general-purpose API to fetch platform process logs, restart the hosted app, or perform arbitrary deployment administration. The app can expose only application-level, sanitized diagnostics that it deliberately records. Platform logs and deployment controls remain in the provider's own interface.

The connected GitHub integration supports repository inspection and permitted GitHub operations. A direct custom ChatGPT-to-Streamlit API action is not available through the connector actions verified in this session. Do not promise unattended, always-on control.

## Architecture

1. **GitHub — source of truth for code and review:** feature branches, pull requests, CI, security checks and workflow evidence.
2. **GitHub Actions — bounded automation:** hourly and manual read-only HTTPS checks against Streamlit's built-in health endpoint, plus repository CI on PR changes. Workflow permissions are `contents: read`.
3. **Streamlit app — application-level diagnostics:** the existing administrator-triggered self-check verifies database connectivity and, for SQLite, required tables, schema version, integrity and foreign-key consistency. It also reports GitHub configuration and environment readiness. Reports omit paths, records, credentials and raw SQL errors.
4. **Approval boundary:** all writes, merges, deployments, restarts, migrations, secret changes and backup retention/recovery remain explicit human-approved operations.
5. **Durable data:** retain the established Google Drive backup strategy; never rely on Community Cloud's local filesystem for authoritative SQLite persistence.

## Delivery checkpoints

- **P18-S001 — Capability and permission audit:** documented in `docs/PHASE-18-CAPABILITY-AND-THREAT-MODEL.md`.
- **P18-S002 — Threat model and operation matrix:** documented; read-only, reversible writes and destructive actions are classified with controls.
- **P18-S003 — Read-only status contract:** implemented in `scripts/check_dashboard_health.py` and covered by `tests/test_dashboard_health_check.py`; no raw log or personal-data exposure.
- **P18-S004 — GitHub Actions automation:** implemented in `.github/workflows/dashboard-health.yml`; hourly and manual; no deployment permissions or production secrets.
- **P18-S005 — ChatGPT workflow verification:** GitHub repository actions were exercised on this feature branch. Direct Streamlit platform administration is not exposed; the safe bridge is GitHub Actions health evidence plus operator-only provider controls.
- **P18-S006 — Acceptance and handoff:** runbook is in `docs/PHASE-18-OPERATOR-RUNBOOK.md`. Exact-head CI and live URL probe remain acceptance gates; see status below.

## Acceptance criteria

- No paid dependency is introduced.
- No existing runtime, dashboard, database or backup folder is stopped, restarted, deleted or modified by this phase.
- Read-only checks reveal no secret, database path, user/project content or raw sensitive log.
- Workflow permissions are least-privilege and CI evidence is tied to the exact commit SHA.
- The documentation distinguishes GitHub repository access, in-app diagnostics, provider-platform logs, and deployment controls.

## Current delivery status

Implementation has been added to `feature/phase-18-free-control-plane` and PR #58 remains open as a draft. The branch now contains the HTTPS health probe, unit tests, hourly/manual GitHub Actions workflow, capability/threat-model document and operator runbook.

**Not yet accepted as complete:** exact-final-head GitHub CI evidence has not been retrieved; the owner must set the repository Actions variable `STREAMLIT_APP_URL` before the scheduled live dashboard probe can run. Without that variable, the workflow correctly reports SKIP. A health endpoint PASS proves server reachability only, not login, database durability or feature correctness.

No production configuration, secrets, database, backups, Colab runtime or running dashboard have been changed. No deployment, restart or merge has been performed. PR merge remains subject to explicit user approval.
