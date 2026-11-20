# Phase 04 — Database System

**Phase objective:** introduce a tested persistence layer for Project Continue's project, task, dependency, and activity-history data.

**Implementation policy:** all source changes are developed in GitHub working branches and merged to main through pull requests. Colab is used for runtime verification, not as the primary source-editing workspace.

## Checkpoint sequence

| Checkpoint | Name | Current status |
|---|---|---|
| PC-P04-S001 | Database Selection | DECISION RECORDED — SQLite |
| PC-P04-S002 | Database Connection | IMPLEMENTED — focused/full tests and file-backed workflow verified; final checkpoint review pending |
| PC-P04-S003 | Project Table | IMPLEMENTED — CRUD, foreign-key, persistence, and cascade behavior verified; final checkpoint review pending |
| PC-P04-S004 | Task Table | IMPLEMENTED — CRUD, ownership, persistence, and deletion behavior verified; final checkpoint review pending |
| PC-P04-S005 | Dependency Table | IMPLEMENTED — same-project constraints, persistence, and cascade behavior verified; final checkpoint review pending |
| PC-P04-S006 | Activity History | IMPLEMENTED — JSON persistence, project/task ownership validation, SQL INSERT/UPDATE triggers, and deletion behavior verified; final checkpoint review pending |
| PC-P04-S007 | Database CRUD | IMPLEMENTED — focused/full tests and realistic file-backed workflow verified; final checkpoint review pending |
| PC-P04-S008 | Database Tests | IMPLEMENTED — 12/12 focused tests and 38/38 full-suite tests passed in Colab; CI passed; final checkpoint review pending |

## Database decision

SQLite through Python's standard-library sqlite3 module is selected for the initial persistence layer. The rationale, limitations, and upgrade conditions are recorded in checkpoints/PC-P04-S001-DATABASE-SELECTION.md.

## Implementation map

- Connection and transaction management: database/connection.py
- Versioned relational schema: database/schema.py
- Project/task/dependency/activity operations: database/repository.py
- Automated acceptance coverage: tests/test_database_connection.py and tests/test_database_repository.py

## Checkpoint completion rules

A checkpoint is not complete merely because code is committed. Each checkpoint must have:
1. A defined scope and acceptance criteria before implementation.
2. A focused implementation in the repository.
3. Automated tests for behavior and rejection/error paths.
4. GitHub Actions CI passing.
5. Runtime verification where the checkpoint requires it.
6. An evidence record naming the exact commit and commands/results.
7. Realistic workflow verification for user-visible or data-integrity behavior.

## Verification evidence — 2026-11-20

All results below apply to PR #12 head commit `dd87af7708b9b5c4ac982dd21b788b311ddaf731` on branch `fix/p04-activity-project-task-integrity`. They do not establish that the commit is already present on `main`.

| Verification | Result | Evidence |
|---|---|---|
| Colab focused database tests | PASS — 12/12 | User-provided Colab output; exit code 0 |
| Colab full test suite | PASS — 38/38 | User-provided Colab output; exit code 0 |
| Real SQLite file-backed workflow | PASS — 10/10 checks | User-provided acceptance output; real temporary SQLite file |
| GitHub Actions CI | PASS | Workflow run #73; job `test`; compile and test steps completed successfully |
| PR state | OPEN — not merged | PR #12; mergeable state reported clean |

The file-backed workflow verified initialization, multiple projects/tasks, dependency and activity persistence, data survival after reopening through new database/repository instances, transaction rollback, foreign-key enforcement, `PRAGMA integrity_check = ok`, task deletion behavior, project cascade deletion, and isolation of an independent project.

The focused test run includes repository and SQL-trigger rejection of cross-project activity/task references on INSERT and UPDATE.

## Scope boundaries

This phase establishes persistence primitives and database-backed records. It does not by itself claim that the project-management UI, task-management workflows, intelligent task engine, GitHub integration, or deployment are complete.

## Current position

S001's SQLite decision is recorded. S002-S008 implementation and the current verification evidence are present. A source-level integrity gap was fixed in PR #12: activity events now enforce that a referenced task belongs to the same project, both in the repository layer and through SQLite INSERT/UPDATE triggers.

The focused tests, full test suite, GitHub Actions CI, Colab runtime tests, and realistic file-backed SQLite workflow have passed on the PR head commit. PR #12 remains open and unmerged. Final checkpoint-by-checkpoint evidence review and merge to `main` are still pending. No claim is made that the application UI or end-to-end user-facing project workflow is complete.
