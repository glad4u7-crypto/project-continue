# Phase 04 — Database System

**Phase objective:** introduce a tested persistence layer for Project Continue's project, task, dependency, and activity-history data.

**Entry condition:** Phase 03 Core Architecture is complete on `main`.  
**Implementation policy:** all source changes are developed in GitHub working branches and merged to `main` through reviewed pull requests. Colab is used for runtime verification, not as the primary source-editing workspace.

## Checkpoint sequence

| Checkpoint | Name | Intended outcome |
|---|---|---|
| PC-P04-S001 | Database Selection | Select and document the database engine and rationale against project requirements |
| PC-P04-S002 | Database Connection | Implement configuration-driven connection management and connection tests |
| PC-P04-S003 | Project Table | Define and migrate the project data model/schema |
| PC-P04-S004 | Task Table | Define task records and their project relationship |
| PC-P04-S005 | Dependency Table | Represent task dependencies with integrity constraints |
| PC-P04-S006 | Activity History | Record relevant project/task changes with timestamps |
| PC-P04-S007 | Database CRUD | Implement and test create, read, update, and delete operations |
| PC-P04-S008 | Database Tests | Add isolated automated tests for schema, constraints, transactions, and CRUD behavior |

## Checkpoint completion rules

A checkpoint is not complete merely because code is committed. Each checkpoint must have:
1. A defined scope and acceptance criteria before implementation.
2. A focused implementation in the repository.
3. Automated tests for its behavior and rejection/error paths.
4. GitHub Actions CI passing.
5. Runtime verification where the checkpoint requires it.
6. A checkpoint evidence record naming the exact commit and commands/results.

## Scope boundaries

This phase establishes persistence primitives and database-backed records. It does not by itself claim that the project-management UI, task-management workflows, intelligent task engine, GitHub integration, or deployment are complete; those belong to later roadmap phases.

## Initial state

**PC-P04-S001: NOT STARTED.** Database technology selection is intentionally the first checkpoint; no database engine is preselected by this plan.
