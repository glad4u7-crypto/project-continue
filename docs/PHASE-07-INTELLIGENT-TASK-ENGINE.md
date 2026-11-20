# PHASE 07 — Intelligent Task Engine

**Objective:** provide deterministic task ranking, explainable priority scoring, dependency analysis, next-task selection, blocked-task detection, recommendations, completion verification, and automated tests.

## Checkpoint register

| Checkpoint | Scope | Implementation status |
|---|---|---|
| PC-P07-S001 | Task Ranking | Implemented; focused/full CI passed; exact-SHA Colab acceptance pending |
| PC-P07-S002 | Priority Calculation | Implemented; deterministic 0–100 explainable score |
| PC-P07-S003 | Dependency Analysis | Implemented; direct/transitive prerequisites, pending items and readiness |
| PC-P07-S004 | Next Task Selection | Implemented; selects highest-scoring ready todo/in-progress task |
| PC-P07-S005 | Blocked Task Detection | Implemented; explicit blocked state and unfinished/cyclic prerequisite detection |
| PC-P07-S006 | Recommendation Engine | Implemented; start/continue/unblock actions |
| PC-P07-S007 | Completion Verification | Implemented; verifies done status and prerequisite completion |
| PC-P07-S008 | Intelligent Engine Tests | Implemented; focused tests and full CI passed |

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

Dependency analysis walks prerequisite graphs and reports transitive prerequisites. A task is ready only when every prerequisite is done and no cycle is found. Next-task selection considers only ready `todo` and `in_progress` tasks. Recommendations distinguish `start`, `continue`, and `unblock`. Completion verification checks task status and prerequisites.

The engine is read-only: it does not update task records, add schema changes, or introduce runtime dependencies. Existing repository safeguards reject dependency cycles and cross-project dependency links.

## Runtime acceptance (Colab)

After syncing the exact target SHA, run:

```bash
git rev-parse HEAD
python -m pip install -r requirements.txt
python -m compileall -q .
python -m pytest -q
python scripts/phase07_acceptance.py
```

The acceptance script creates an isolated temporary SQLite database, exercises every Phase 07 capability end-to-end, and deletes its temporary data automatically. It does not touch the user's existing project database.

## Verification record

- PR #16 merged to `main`; merge commit: `c152783f83145831fa79be1e22a138085bb949f0`.
- GitHub Actions PR run #127: Python 3.11.18, compileall PASS, full suite **86 passed**.
- Colab exact-SHA runtime acceptance remains required. Do not mark Phase 07 fully accepted until the user runs the commands above against the exact merged `main` SHA and shares the output.
