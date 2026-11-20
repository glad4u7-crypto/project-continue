# Phase 04 — Database System

**Phase objective:** introduce a tested persistence layer for Project Continue's project, task, dependency, and activity-history data.

**Implementation policy:** all source changes are developed in GitHub working branches and merged to main through pull requests. Colab is used for runtime verification, not as the primary source-editing workspace.

## Checkpoint sequence

| Checkpoint | Name | Current status |
|---|---|---|
| PC-P04-S001 | Database Selection | DECISION RECORDED — SQLite |
| PC-P04-S002 | Database Connection | IMPLEMENTED — verification pending |
| PC-P04-S003 | Project Table | NOT STARTED |
| PC-P04-S004 | Task Table | NOT STARTED |
| PC-P04-S005 | Dependency Table | NOT STARTED |
| PC-P04-S006 | Activity History | NOT STARTED |
| PC-P04-S007 | Database CRUD | NOT STARTED |
| PC-P04-S008 | Database Tests | NOT STARTED |

## Database decision

SQLite through Python's standard-library sqlite3 module is selected for the initial persistence layer. The rationale, limitations, and upgrade conditions are recorded in checkpoints/PC-P04-S001-DATABASE-SELECTION.md.

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

S001 decision is recorded. S002 connection implementation is in place and awaiting CI/runtime verification. Later schema and CRUD checkpoints remain open.
