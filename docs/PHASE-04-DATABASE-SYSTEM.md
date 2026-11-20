# Phase 04 — Database System

**Phase objective:** introduce a tested persistence layer for Project Continue's project, task, dependency, and activity-history data.

**Implementation policy:** all source changes are developed in GitHub working branches and merged to main through pull requests. Colab is used for runtime verification, not as the primary source-editing workspace.

## Checkpoint sequence

| Checkpoint | Name | Current status |
|---|---|---|
| PC-P04-S001 | Database Selection | DECISION RECORDED — SQLite |
| PC-P04-S002 | Database Connection | IMPLEMENTED — verification pending |
| PC-P04-S003 | Project Table | IMPLEMENTED — verification pending |
| PC-P04-S004 | Task Table | IMPLEMENTED — verification pending |
| PC-P04-S005 | Dependency Table | IMPLEMENTED — verification pending |
| PC-P04-S006 | Activity History | IMPLEMENTED — verification pending |
| PC-P04-S007 | Database CRUD | IMPLEMENTED — verification pending |
| PC-P04-S008 | Database Tests | IMPLEMENTED — verification pending |

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

## Scope boundaries

This phase establishes persistence primitives and database-backed records. It does not by itself claim that the project-management UI, task-management workflows, intelligent task engine, GitHub integration, or deployment are complete.

## Current position

S001 decision is recorded. S002-S008 implementation is present in the Phase 04 working branch. All eight checkpoints await CI and runtime verification before final completion status can be assigned.
