# PHASE 07 — Intelligent Task Engine

**Objective:** provide deterministic task ranking, explainable priority scoring, dependency analysis, next-task selection, blocked-task detection, recommendations, completion verification, and automated tests.

## Checkpoint register

| Checkpoint | Scope | Implementation status |
|---|---|---|
| PC-P07-S001 | Task Ranking | Implemented; focused and full CI tests passed; Colab runtime acceptance pending |
| PC-P07-S002 | Priority Calculation | Implemented; deterministic 0–100 explainable score and fixed-date tests |
| PC-P07-S003 | Dependency Analysis | Implemented; direct/transitive prerequisites, pending items, readiness and defensive cycle detection |
| PC-P07-S004 | Next Task Selection | Implemented; selects highest-scoring ready todo/in-progress task; returns none when unavailable |
| PC-P07-S005 | Blocked Task Detection | Implemented; explicit blocked state and unfinished/cyclic prerequisite detection |
| PC-P07-S006 | Recommendation Engine | Implemented; start/continue/unblock actions with deterministic score ordering and limit |
| PC-P07-S007 | Completion Verification | Implemented; verifies done status and all prerequisite completion |
| PC-P07-S008 | Intelligent Engine Tests | Implemented; focused regression tests and full CI verification |

## Public API

All functionality is exposed through `services.IntelligentTaskEngine`:

- `rank_tasks(tasks)` and `rank_project_tasks(project_id)`
- `calculate_priority(task, as_of=None)` and `calculate_project_priorities(project_id, as_of=None)`
- `analyze_dependencies(task_id)`
- `select_next_task(project_id, as_of=None)`
- `detect_blocked_tasks(project_id)`
- `recommend_actions(project_id, as_of=None, limit=5)`
- `verify_completion(task_id)`

## Decision rules

Priority scoring is a deterministic 0–100 score: base priority points (critical 40, high 30, medium 20, low 10), workflow-state adjustment (in progress +15, todo +10, blocked −20, done = 0), and due-date urgency (overdue +30; due within 1/3/7/14 days +25/+20/+12/+6). Scores are clamped to 0–100 and include human-readable reasons. Callers can supply `as_of` for reproducible decisions.

Dependency analysis walks the prerequisite graph and reports transitive prerequisites. A task is ready only when every prerequisite is done and no cycle is found. Next-task selection considers only ready `todo` and `in_progress` tasks. Recommendations distinguish `start`, `continue`, and `unblock`. Completion verification independently checks task status and prerequisites.

The engine is read-only: it does not update task records, add schema changes, or introduce runtime dependencies. Existing repository safeguards reject dependency cycles and cross-project dependency links.

## Verification policy

GitHub CI is required to pass Python compilation and the complete pytest suite before merge. The implementation's CI result does not substitute for the separate Colab runtime acceptance at the exact merged `main` SHA. Do not report Phase 07 as fully accepted until that runtime check is also complete.
