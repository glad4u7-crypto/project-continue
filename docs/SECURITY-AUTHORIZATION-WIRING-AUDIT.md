# Authorization Wiring Audit — Current Repository Status

**Audit refreshed:** 2026-11-25  
**Repository:** `glad4u7-crypto/project-continue`  
**Audited baseline:** `main` after PR #45 and PR #44; see latest main commit in GitHub  
**Authorization implementation:** `18d5b4320163cd17bbb01f9b610887ed4d3d9fdc`  
**Follow-up:** PR #45 merged as `ed702bea6ef782cd4b20ff7d6c8047f1545c6d1d`  
**Result:** SERVICE/UI AUTHORIZATION AND SELECTED-PROJECT CHECKPOINT ISOLATION MERGED; exact-release browser and host acceptance remain pending.

> This document supersedes the 2026-11-21 audit below. The earlier BLOCKED result accurately described its older baseline, but it is no longer an accurate description of current `main`.

## Current implementation evidence

| Area | Current source | Current control |
|---|---|---|
| Session and principal | `ui/authentication.py`, `services/access_control.py` | HMAC-signed session verification; principal is revalidated against the live enabled account |
| Entry point | `app.py` | Production defaults to admin-only login; `AUTHORIZATION_ENFORCED=true` explicitly enables project-member login |
| Project operations | `services/project_management.py` | Request-scoped authorization context; project read filtering and manage checks for update/archive/restore; controlled owner bootstrap |
| Task operations | `services/task_management.py` | Read/write checks use the task's canonical project ID resolved from the database |
| AI Brain | `services/ai_brain.py`, `ui/ai_brain.py` | Project read/write checks; approval decision is bound to requester and project |
| Automation | `services/automation_engine.py`, `ui/automation.py` | Project-scoped rules/notifications; global schedules and unscoped alerts require admin |
| Memory/checkpoints | `services/memory_checkpoint_engine.py`, `ui/memory_checkpoint.py` | Project-scoped memory, sessions, decisions, checkpoint reads, recovery and resume; selected-project binding and UI state reset are merged |
| GitHub panel | `app.py` | Restricted to administrator context when membership authorization is active |

## Authorization policy

- Owner: read/write/manage within the owned project.
- Editor: read/write within a project; cannot manage project metadata or membership.
- Viewer: read-only project access.
- Non-member: denied.
- Disabled account, invalid/forged principal, or invalid session: denied.
- Global administrator: operator-level access; privileged bypasses are explicit and revalidated against the live account record.

Resource authorization derives the project ID from canonical database records, not from caller-supplied task/project metadata. The membership mode is opt-in; production remains admin-only unless the operator explicitly enables it.

## Automated regression coverage present

`tests/test_authorization.py` exercises the role matrix, forged/missing principals, canonical resource scope, disabled accounts, project/task service boundaries, memory/checkpoint recovery, AI approval ownership, and admin-only automation controls using isolated SQLite databases.

PR #45 merged the selected-project `project_id` scoping for checkpoint lookup, recovery and resume, plus a regression test proving a checkpoint identifier cannot be used through a different selected project. It also clears stale memory/checkpoint UI state when the selected project or signed-in principal changes. PR #41 was closed as superseded because it was based on pre-authorization code.

## Remaining release gates

1. The exact merged release must retain passing full regression, dependency audit and secret scan evidence; rerun on each release candidate.
2. Browser acceptance must verify unauthenticated denial and Owner/Editor/Viewer/Non-member behavior across two projects.
3. The operator must configure `SESSION_SIGNING_KEY`, provision the initial administrator, enable membership mode deliberately, bootstrap owners for existing projects, and grant memberships.
4. The selected host must provide HTTPS, durable private storage, secret management, scheduled backups, monitoring and a verified isolated restore drill.
5. Public exposure and final sign-off remain blocked until these independent gates are evidenced.

## Decision

- Authorization primitives: IMPLEMENTED.
- Service/UI project-membership wiring: IMPLEMENTED IN SOURCE.
- Selected-project checkpoint binding: ADDED IN REVIEW BRANCH; CI pending.
- Exact candidate SHA CI: PENDING.
- Browser and real-host authorization acceptance: PENDING.
- Public multi-user production approval: BLOCKED pending the release gates above.

No live database, runtime, Colab session, Streamlit process, secret or production host was accessed or changed by this audit.
