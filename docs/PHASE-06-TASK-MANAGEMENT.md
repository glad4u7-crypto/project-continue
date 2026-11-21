# Phase 06 — Task Management

**Objective:** deliver task creation, assignment, priority/status control, dependency-aware completion, editing and automated verification.

**Assignment model:** optional free-text name or email. It is not an authenticated user identity.

## Checkpoint register

| Checkpoint | Scope | Implementation and verification |
|---|---|---|
| PC-P06-S001 | Create Task | Implemented; isolated file-backed acceptance PASS in CI |
| PC-P06-S002 | Task Assignment | Implemented; set/update/clear covered by acceptance workflow |
| PC-P06-S003 | Task Priority | Implemented; four validated priority levels and filters |
| PC-P06-S004 | Task Status | Implemented; four workflow states and filters |
| PC-P06-S005 | Task Dependencies | Implemented; same-project edges, cycle prevention and completion gate covered |
| PC-P06-S006 | Task Update | Implemented; metadata updates and activity events covered |
| PC-P06-S007 | Task Completion | Implemented; prerequisite-aware completion and idempotent done state covered |
| PC-P06-S008 | Task Management Tests | Seven-group isolated acceptance and subprocess test PASS in PR #27 CI |

## Design and safety

- SQLite schema v2 adds nullable assignee and migrates v1 databases in place.
- Use cases live in `services/task_management.py`; Streamlit controls are integrated into project details.
- Dependencies must be same-project and acyclic. All prerequisites must be done before completion.
- Assignee is a descriptive label only; no login, identity verification, notification or authorization is implied.
- Mutations write activity events. No task deletion control is exposed in the dashboard.

## Reproducible automated acceptance

Run:

```bash
python -m compileall -q .
python -m pytest -q tests/test_phase06_acceptance.py
python scripts/phase06_acceptance.py
```

The isolated workflow covers task creation, assignment, priority, due date, search/filter, updates, assignment clearing, dependency add/remove, cycle and cross-project rejection, dependency-aware completion, activity history, file-backed close/reopen persistence, SQLite integrity, and verified backup contents. It uses a temporary database and does not touch the user's normal project database.

## Verification record

- Implementation PR #14 merged into main.
- Historical PR CI run #108 and post-merge run #109: SUCCESS; 72 tests passed.
- New acceptance and Streamlit smoke tests merged through PR #27.
- PR #27 CI: **SUCCESS**, full suite **167 passed**, statement coverage **96%** on Python 3.11.18.
- Merge commit: `5d0610d3f9118cbcb3fe621280f6fa8e8fa5e3f9`.

**Current disposition:** implementation and repository CI acceptance PASS. Exact-current-main-SHA Colab runtime acceptance and all eight manual browser UI checkpoints remain pending. Do not mark the entire phase fully accepted until those gates have evidence.
