# Phase 06 — Task Management

**Objective:** deliver task creation, assignment, priority/status control, dependency-aware completion, editing and automated verification.

**Assignment model:** optional free-text name or email. It is not an authenticated user identity.

## Checkpoint register

| Checkpoint | Scope | Implementation and verification |
|---|---|---|
| PC-P06-S001 | Create Task | Implemented; isolated acceptance workflow added; CI pending |
| PC-P06-S002 | Task Assignment | Implemented; set/update/clear covered by acceptance workflow |
| PC-P06-S003 | Task Priority | Implemented; four validated priority levels and filters |
| PC-P06-S004 | Task Status | Implemented; four workflow states and filters |
| PC-P06-S005 | Task Dependencies | Implemented; same-project edges, cycle prevention and completion gate |
| PC-P06-S006 | Task Update | Implemented; metadata updates and activity events |
| PC-P06-S007 | Task Completion | Implemented; prerequisite-aware completion and idempotent done state |
| PC-P06-S008 | Task Management Tests | New 7-group file-backed acceptance and subprocess test added; CI and Colab pending |

## Design and safety

- SQLite schema v2 adds nullable assignee and migrates v1 databases in place.
- Use cases live in `services/task_management.py`; Streamlit controls are integrated into project details.
- Dependencies must be same-project and acyclic. All prerequisites must be done before completion.
- Assignee is a descriptive label only; no login, identity verification, notification or authorization is implied.
- Mutations write activity events. No task deletion control is exposed in the dashboard.

## Automated acceptance added

Run:

```bash
python -m compileall -q .
python -m pytest -q tests/test_phase06_acceptance.py
python scripts/phase06_acceptance.py
```

The isolated workflow covers task creation, assignment, priority, due date, search/filter, updates, assignment clearing, dependency add/remove, cycle and cross-project rejection, dependency-aware completion, activity history, file-backed close/reopen persistence, SQLite integrity, and verified backup contents. It uses a temporary database and does not touch the user's normal project database.

## Existing verification

- PR #14 merged into main.
- PR CI run #108 and post-merge run #109: SUCCESS; 72 tests passed.
- The above historical CI does not substitute for the newly added acceptance tests.
- The new acceptance test and Streamlit smoke test require a successful CI run before their status can be upgraded.
- Manual Colab dashboard acceptance remains pending; use the checklist in `docs/STREAMLIT-UI-ACCEPTANCE.md`.

**Current disposition:** implementation merged; automated acceptance added but not yet verified on CI; Colab and manual UI acceptance pending. Do not mark all eight checkpoints PASS until those gates have evidence.
