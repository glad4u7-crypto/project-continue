# Streamlit UI — Automated and Environment Acceptance

**Purpose:** distinguish repeatable CI acceptance from checks that require a specifically selected deployment host. CI browser tests use a disposable SQLite database and must never touch a user's live database or running dashboard.

## Automated CI acceptance

The Dashboard Browser Acceptance workflow launches Streamlit on an ephemeral local port and uses Chromium against a temporary database. It currently exercises:

- Dashboard hydration and required sections.
- Project create, search, open, archive and restore.
- Task create, edit, status change and persistence after page reload.
- Mock AI suggestion with explicit approval.
- Automation schedule create and pause.
- Project memory save.
- Checkpoint create and preview-only recovery.
- Session history and decision recording.
- Read-only self-check diagnostics.

The workflow must pass on the exact pull-request head commit. Its success is evidence for the workflows above only; it is not evidence that an external Colab/production host is configured or deployed.

Other CI workflows cover Python 3.11/3.13 regression, security/operations, container build and smoke checks, and isolated PostgreSQL integration. Report skipped tests separately; never count them as passing.

## Acceptance boundaries still requiring a selected host

| Gate | Required evidence | Current interpretation |
|---|---|---|
| Role/authorization matrix | Two synthetic users/projects; prove cross-project reads and writes are denied | Not covered by the current Chromium smoke workflow |
| Dependency UI edge cases | Add/remove, cycle rejection, cross-project rejection and blocked completion in the rendered UI | Service-level coverage is not UI acceptance |
| GitHub integration panel/API | Real configured repository connection or safe actionable failure on the selected host | CI configuration is not live integration verification |
| Deployment/release identity | Exact deployed commit SHA matches the approved release SHA | Cannot be inferred from GitHub CI |
| Host operations | HTTPS, secret management, persistent storage, scheduler and off-host backup evidence | Requires the chosen host/operator environment |
| Restore drill | Restore an isolated backup copy and verify records/integrity without overwriting live data | Production restore is not implied by unit/CI tests |

Mark unavailable host gates BLOCKED — host evidence not supplied, not PASS. These are deployment/operator acceptance gates; they are not instructions for the user to perform manual QA.

## Safety requirements

- Do not reboot or restart the existing Colab runtime or stop/restart an already-running Streamlit dashboard without explicit authorization.
- Do not run destructive acceptance against the live database.
- Use disposable test databases and isolated backup/restore copies.
- Do not modify existing backup folders; new backups must use the project's single approved destination.
- Do not expose secrets, database paths, personal project/task contents, or unredacted diagnostic artifacts.
- Do not claim a release is production-ready while any required host gate remains blocked.

## Release decision

A green CI run establishes code-level acceptance for the automated coverage listed above. A release may be called production-ready only after the selected host's deployment identity, security, persistence, integration, backup and restore evidence has been recorded and all required acceptance gates are satisfied.