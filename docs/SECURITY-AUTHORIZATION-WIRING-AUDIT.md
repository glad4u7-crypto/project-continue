# Authorization Wiring Audit — Production Release Gate

**Audit date:** 2026-11-21  
**Audited branch:** `main`  
**Audited baseline:** `4fb3012a5c8c639bbef1af00d83f830f96cacd56`  
**Result:** BLOCKED — authorization primitives exist, but the current application feature paths do not consistently enforce them.

## Executive summary

The repository has a SQLite-backed identity and project-membership service in `services/access_control.py`. Its unit tests exercise role checks and cross-project denial. This does not establish end-to-end authorization: the production entry point currently admits only authenticated administrators, while the feature UI/service paths below do not pass a verified principal into project-scoped operations or call `require_project`.

Do not describe the application as multi-user/tenant secure. Do not publicly expose it until the controls below are implemented, tested and reviewed. The admin-only production gate is a restricted operator boundary, not evidence of project membership enforcement for general users.

## Evidence observed

| Area | Source | Finding |
|---|---|---|
| Production login | `ui/authentication.py` | Verifies a signed session and admits only principals whose global role is `admin`. |
| Application entry | `app.py` | Calls the production authentication gate before rendering feature pages; this is a global admin gate, not per-project authorization. |
| Project/task UI | `ui/project_management.py` | Creates `ProjectManagementService` and `TaskManagementService` without an authenticated principal or access-control dependency. |
| Project service | `services/project_management.py` | Public list/create/get/update/archive/restore methods operate directly on the repository without project membership checks. |
| Task service | `services/task_management.py` | Public task read/write/dependency/completion methods operate by project/task identifiers without principal checks. |
| AI UI | `ui/ai_brain.py` | Lists all active projects and invokes project context/suggestion and approval operations without a project authorization check. |
| Automation UI | `ui/automation.py` | Lists/creates/runs schedules and notifications without a verified principal or project-level access decision. |
| Memory UI | `ui/memory_checkpoint.py` | Reads/writes project memory, checkpoints, session history, decisions and recovery without a verified principal. |
| Authorization tests | `tests/test_access_control.py` | Tests the access-control primitive in isolation (role matrix, cross-project denial, admin access, audit and login throttling); does not prove UI/service integration. |

## Required remediation

1. **Principal propagation:** expose the verified production principal through a typed, server-side request/session context. Never accept a user ID, role or project permission from a form, query parameter or client-controlled state.
2. **Project service enforcement:** inject an authorization dependency into project and task use cases. Enforce read/write/manage permission inside service methods, not only in Streamlit rendering. Define and test the bootstrap/creation ownership flow explicitly.
3. **AI Brain:** authorize project read before context construction and project-scoped approval access. Bind approval request ownership to the authenticated principal; prevent cross-user request decisions.
4. **Automation:** define whether schedules are global or project-scoped. For project-scoped rules/notifications enforce read/write/manage at each operation; restrict global database health checks to operators.
5. **Memory/checkpoints:** enforce project read/write on every memory, checkpoint, session, decision, handoff and recovery operation. Verify checkpoint ownership before preview or apply.
6. **Admin semantics:** document whether global admin bypass is intentional, audit every bypass, and ensure disabled accounts/session revocation remain effective.
7. **Integration tests:** exercise real services and UI-facing workflows with owner/editor/viewer/admin identities across two projects. Assert both allowed and denied reads/writes, task-ID-to-project resolution, automation, AI approval and checkpoint recovery.
8. **Regression/security review:** run the full test suite, static/secret checks and CI on the exact proposed SHA; have a reviewer inspect the authorization boundary before public exposure.

## Acceptance matrix

| Principal | Project read | Task write | Membership manage |
|---|---:|---:|---:|
| Owner of project | Allow | Allow | Allow |
| Editor of project | Allow | Allow | Deny |
| Viewer of project | Allow | Deny | Deny |
| Non-member | Deny | Deny | Deny |
| Disabled account / invalid session | Deny | Deny | Deny |
| Global admin | Allow only if explicit admin-bypass policy is retained | Same | Same |

Tests must cover two different project IDs and must resolve a task's owning project server-side before authorizing task operations.

## Release decision

- Repository authorization primitives: **IMPLEMENTED**
- Production admin sign-in gate: **IMPLEMENTED**
- End-to-end project membership enforcement: **NOT VERIFIED / INCOMPLETE**
- Service/UI integration tests: **NOT PRESENT IN THE AUDITED PATHS**
- Public multi-user production approval: **BLOCKED**

## Safety boundary

This audit changed no application runtime, Colab runtime, Streamlit process, database or user data. Remediation must use isolated test databases. Never perform a live migration or restart the user's running dashboard as part of this work.
