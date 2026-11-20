# Phase 04 — Database System

**Phase objective:** introduce a tested persistence layer for Project Continue's project, task, dependency, and activity-history data.

**Implementation policy:** all source changes are developed in GitHub working branches and merged to main through pull requests. Colab is used for runtime verification, not as the primary source-editing workspace.

## Checkpoint sequence

| Checkpoint | Name | Current status |
|---|---|---|
| PC-P04-S001 | Database Selection | DECISION RECORDED — SQLite |
| PC-P04-S002 | Database Connection | IMPLEMENTED — file-backed tests previously passed; shared in-memory persistence hardening added; latest retest pending |
| PC-P04-S003 | Project Table | IMPLEMENTED — CRUD, foreign-key, persistence, and cascade behavior previously verified; final retest/review pending |
| PC-P04-S004 | Task Table | IMPLEMENTED — CRUD, ownership, persistence, and deletion behavior previously verified; final retest/review pending |
| PC-P04-S005 | Dependency Table | IMPLEMENTED — repository checks previously passed; SQLite UPDATE ownership and INSERT/UPDATE cycle triggers added; latest retest pending |
| PC-P04-S006 | Activity History | IMPLEMENTED — JSON persistence, project/task ownership validation, SQL INSERT/UPDATE triggers, and deletion behavior previously verified; final retest/review pending |
| PC-P04-S007 | Database CRUD | IMPLEMENTED — repository and file-backed workflow previously verified; latest retest/review pending |
| PC-P04-S008 | Database Tests | IMPLEMENTED — prior 12/12 focused and 38/38 full-suite tests passed; latest regression suite and CI pending |

## Database decision

SQLite through Python's standard-library sqlite3 module is selected for the initial persistence layer. The rationale, limitations, and upgrade conditions are recorded in checkpoints/PC-P04-S001-DATABASE-SELECTION.md.

## Implementation map

- Connection and transaction management: database/connection.py
- Versioned relational schema: database/schema.py
- Project/task/dependency/activity operations: database/repository.py
- Automated acceptance coverage: tests/test_database_connection.py and tests/test_database_repository.py
- S002-S008 acceptance criteria: checkpoints/PC-P04-S002-TO-S008-DATABASE-ACCEPTANCE.md

## Checkpoint completion rules

A checkpoint is not complete merely because code is committed. Each checkpoint must have:
1. A defined scope and acceptance criteria before implementation.
2. A focused implementation in the repository.
3. Automated tests for behavior and rejection/error paths.
4. GitHub Actions CI passing on the exact current PR head.
5. Runtime verification where the checkpoint requires it.
6. An evidence record naming the exact commit and commands/results.
7. Realistic workflow verification for user-visible or data-integrity behavior.

## Historical verification evidence — 2026-11-20

The following earlier results apply to code commit dd87af7708b9b5c4ac982dd21b788b311ddaf731, not to the latest audit-hardening commits:

| Verification | Result | Evidence |
|---|---|---|
| Colab focused database tests | PASS — 12/12 | User-provided Colab output; exit code 0 |
| Colab full test suite | PASS — 38/38 | User-provided Colab output; exit code 0 |
| Real SQLite file-backed workflow | PASS — 10/10 checks | User-provided Colab output; temporary SQLite file |
| GitHub Actions CI | PASS | Workflow run #73; job test; compile and test steps completed successfully |

The file-backed workflow verified initialization, multiple projects/tasks, dependency and activity persistence, data survival after reopening through new database/repository instances, transaction rollback, foreign-key enforcement, PRAGMA integrity_check = ok, task deletion behavior, project cascade deletion, and isolation of an independent project.

## Audit hardening added after the historical verification

A second source-level review identified two gaps and added regression coverage on the PR branch:

1. Dependency integrity: the repository API already rejected cross-project dependencies and cycles, but direct SQL UPDATE could bypass same-project ownership, and direct SQL could bypass cycle prevention. SQLite BEFORE INSERT and BEFORE UPDATE triggers now enforce both invariants.
2. Shared in-memory database: Database(':memory:') previously created a fresh independent database for each short-lived connection, so repository operations could not share schema/data. A private shared-memory URI and anchor connection now preserve state across connection contexts, with an explicit close() method.

New tests were added for dependency UPDATE ownership, dependency cycle rejection on INSERT/UPDATE, and repository persistence using the shared in-memory database.

The updated database-focused suite is expected to contain 15 tests and the full suite 41 tests. These are expected counts only; they are not marked passed until the latest Colab output confirms them. The earlier CI run does not cover these new commits.

## Scope boundaries

This phase establishes persistence primitives and database-backed records. It does not by itself claim that the project-management UI, task-management workflows, intelligent task engine, GitHub integration, or deployment are complete.

## Current position

S001's SQLite decision is recorded. S002-S008 implementation is present and now has explicit checkpoint-by-checkpoint acceptance criteria. The latest audit fixes are committed to PR #12, but the latest focused tests, full suite, CI, and Colab retest are pending. PR #12 remains open and unmerged. No Phase 04 checkpoint is marked complete based only on implementation. No claim is made that the application UI or end-to-end user-facing project workflow is complete.
