# PHASE 06 — Task Management

**Objective:** deliver task creation, assignment, priority/status control, dependency-aware completion, editing and automated verification.

**Assignment model:** optional free-text name or email. It is not an authenticated user identity; a future account system can replace it with user IDs.

## Checkpoint register

| Checkpoint | Scope | Evidence | Status |
|---|---|---|---|
| PC-P06-S001 | Create Task | Service, generated IDs, validation, persistence, UI and activity event | IMPLEMENTED — verification pending |
| PC-P06-S002 | Task Assignment | Optional free-text assignee, update/clear and explicit UI disclosure | IMPLEMENTED — verification pending |
| PC-P06-S003 | Task Priority | Four validated priorities, editing and filters | IMPLEMENTED — verification pending |
| PC-P06-S004 | Task Status | Four task states, lifecycle controls and filters | IMPLEMENTED — verification pending |
| PC-P06-S005 | Task Dependencies | Same-project edges, cycle prevention, add/remove and completion gate | IMPLEMENTED — verification pending |
| PC-P06-S006 | Task Update | Editable metadata and audit event | IMPLEMENTED — verification pending |
| PC-P06-S007 | Task Completion | Explicit completion, idempotent done state and dependency gate | IMPLEMENTED — verification pending |
| PC-P06-S008 | Task Management Tests | Migration regression, unit/integration tests, CI and Colab acceptance | PENDING |

## Design and safety

- SQLite schema v2 adds nullable assignee and migrates v1 databases in place.
- Use cases live in services/task_management.py; Streamlit controls are integrated into project details.
- Dependencies must be same-project and acyclic. All prerequisites must be done before completion.
- Assignee is a descriptive label only; no login, identity verification, notification or authorization is implied.
- Mutations write activity events. No task deletion control is exposed in the dashboard.
- No runtime dependencies are added.

## Verification record

No checkpoint is PASS until code review, automated tests, GitHub Actions, final-main Colab SHA verification and user dashboard acceptance are evidenced.
