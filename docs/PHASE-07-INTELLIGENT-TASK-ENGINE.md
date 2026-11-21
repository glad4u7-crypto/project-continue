# Phase 07 — Intelligent Task Engine

**Objective:** provide deterministic task ranking, explainable priority scoring, dependency analysis, next-task selection, blocked-task detection, recommendations, completion verification, and automated tests.

## Checkpoint register

| Checkpoint | Scope | Implementation | Evidence state |
|---|---|---|---|
| PC-P07-S001 | Task Ranking | Deterministic task ranking | Implemented; CI test pending |
| PC-P07-S002 | Priority Calculation | Explainable 0–100 priority score | Implemented |
| PC-P07-S003 | Dependency Analysis | Direct/transitive prerequisites and readiness | Implemented |
| PC-P07-S004 | Next Task Selection | Highest-scoring ready todo/in-progress task | Implemented |
| PC-P07-S005 | Blocked Task Detection | Unfinished/cyclic prerequisite detection | Implemented |
| PC-P07-S006 | Recommendation Engine | Start/continue/unblock actions | Implemented |
| PC-P07-S007 | Completion Verification | Task status and prerequisite verification | Implemented |
| PC-P07-S008 | Intelligent Engine Tests | Isolated acceptance subprocess test added | CI pending |

## Public API

All functionality is exposed through `services.IntelligentTaskEngine`:

- `rank_tasks(tasks)` and `rank_project_tasks(project_id)`
- `calculate_priority(task, as_of=None)` and `calculate_project_priorities(project_id, as_of=None)`
- `analyze_dependencies(task_id)`
- `select_next_task(project_id, as_of=None)`
- `detect_blocked_tasks(project_id)`
- `recommend_actions(project_id, as_of=None, limit=5)`
- `verify_completion(task_id)`

Priority scoring is deterministic and explainable. Dependency analysis reports transitive prerequisites and readiness. The engine is read-only and does not mutate task records.

## Isolated acceptance

Run:

```bash
python -m compileall -q .
python -m pytest -q tests/test_phase07_acceptance.py
python scripts/phase07_acceptance.py
```

The acceptance script creates and removes its own temporary SQLite database. It exercises ranking, score/reasons, dependency analysis, next actionable task, blocked detection, recommendations, and dependency-aware completion. A user-supplied Phase 07 runtime acceptance transcript was previously reported as PASS; the prior transcript did not preserve an exact SHA in the repository evidence. The new subprocess test makes this acceptance reproducible in CI.

## Verification record

- PR #16 merged into main.
- Historical PR CI run #127: Python 3.11.18, compile PASS, 86 tests passed.
- Prior user-reported runtime acceptance included all eight capability checks and isolated database confirmation.
- Exact-current-main-SHA Colab re-run and CI for the new acceptance wrapper remain pending.

**Current disposition:** implementation complete; prior runtime result reported PASS; reproducible CI acceptance and exact-current-SHA Colab recheck pending.
