# Project Continue — User Guide

## 1. What the application does

Project Continue is a Streamlit application for organizing projects and tasks, tracking dependencies, viewing AI-assisted recommendations, managing automation, recording durable project memory/checkpoints, and inspecting a GitHub repository in read-only mode.

The exact features visible depend on the release and enabled configuration. AI features are disabled by default unless an approved provider is configured.

## 2. Sign-in and access

In production, the application requires a signed-in administrator by default. The operator may explicitly enable the project-member sign-in flow by setting `AUTHORIZATION_ENFORCED=true`. In that mode, Owner, Editor and Viewer accounts can access only projects where they have membership, with role-specific permissions. Sign out from the sidebar when finished.

The operator must configure `SESSION_SIGNING_KEY` (at least 32 bytes, stored only in the host secret manager), provision the initial administrator, bootstrap ownership for existing projects, and grant memberships before enabling multi-user access. A successful sign-in does not grant access to every project.

**Release limitation:** service-level authorization wiring is implemented in the repository. Exact-release CI, manual browser checks across two projects/roles, and host-specific configuration are still required before a public multi-user production approval.

Do not share passwords, session tokens, API keys, database files or backup files.

## 3. Projects

1. Open the Project Management area.
2. Create a project with a clear name and description.
3. Use search/filter controls to locate a project.
4. Update lifecycle/status fields when the project progresses.
5. Keep project identifiers and ownership information in your operational records.

Use one project per independently tracked body of work. Do not store secrets or personal sensitive information in descriptions or memory.

## 4. Tasks and dependencies

1. Select the relevant project.
2. Create a task with a concise title and actionable description.
3. Set priority, status and assignee label as appropriate.
4. Add dependencies when one task must finish before another.
5. Complete prerequisite tasks before marking dependent work complete.

Assignees are labels, not authenticated user identities. The dependency engine rejects cycles and prevents completion while prerequisites remain unfinished.

## 5. AI assistance

AI Brain is advisory. Review generated recommendations before acting. Do not paste passwords, tokens, private keys, confidential customer records or other secrets into prompts. A recommendation is not an authorization to execute a destructive or external action.

If AI is disabled, the application should continue to support its non-AI project workflows.

## 6. Automation

Automation schedules and retry behavior are governed by configured rules. Confirm the intended action and schedule before enabling an automation. A Colab session that disconnects is not a reliable always-on scheduler; production automation must run on an approved always-on host.

## 7. GitHub integration

The current GitHub integration is read-only. Public repositories may be inspected without a token subject to GitHub rate limits. Private repository access requires an appropriately scoped read-only token configured by the operator. Never paste tokens into task descriptions or commit them to Git.

## 8. Memory, checkpoints and resume

Memory/checkpoint features retain project-scoped notes and history, create integrity-checked snapshots, produce handoff notes and support preview-first recovery.

- Do not store secrets in memory.
- Verify a checkpoint before relying on it.
- Review a recovery preview before confirming it.
- Recovery is additive and must not be treated as a replacement for a verified database backup.
- Preserve the original database and create a separate backup before operational recovery.

## 9. Troubleshooting

| Symptom | Safe first response |
|---|---|
| Sign-in unavailable | Contact the operator; do not repeatedly guess credentials |
| Project/task not visible | Check selected project and filters; ask the operator to verify access |
| GitHub API limit/error | Retry later or ask operator to review read-only token scope |
| AI unavailable | Confirm AI is enabled and provider configuration is valid; continue non-AI work |
| Automation did not run | Check the always-on scheduler and its sanitized logs |
| Database/health error | Stop making changes and contact the operator; do not delete or replace database files |
| Recovery warning | Do not proceed until backup integrity and destination have been reviewed |

## 10. Data handling and support

Keep the SQLite database and backups in private storage with restricted filesystem access. Use the operator's approved support channel for incidents. Include the application release SHA, timestamp and sanitized error type; never include secrets or raw database contents.

## 11. Current release limitations

- Production hosting/provider and live URL are deployment-specific and are not implied by CI success.
- Signed-session and project-membership enforcement are implemented; production defaults to admin-only, while multi-user mode is opt-in and still requires exact-release/browser/host acceptance.
- Host HTTPS, durable volume, secret manager, external backup scheduler, monitoring and restore drill require real-host evidence.
- GitHub integration is read-only.
