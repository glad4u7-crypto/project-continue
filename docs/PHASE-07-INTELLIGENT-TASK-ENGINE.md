# PHASE 07 — Intelligent Task Engine

**Objective:** rank tasks, calculate priority, analyze dependencies, select the next actionable task, detect blocked work, recommend actions, verify completion, and test the complete decision engine.

## Checkpoint register

| Checkpoint | Scope | Status |
|---|---|---|
| PC-P07-S001 | Task Ranking | IMPLEMENTED — focused tests added; GitHub CI PASS; Colab verification pending |
| PC-P07-S002 | Priority Calculation | NOT STARTED |
| PC-P07-S003 | Dependency Analysis | NOT STARTED |
| PC-P07-S004 | Next Task Selection | NOT STARTED |
| PC-P07-S005 | Blocked Task Detection | NOT STARTED |
| PC-P07-S006 | Recommendation Engine | NOT STARTED |
| PC-P07-S007 | Completion Verification | NOT STARTED |
| PC-P07-S008 | Intelligent Engine Tests | NOT STARTED |

## PC-P07-S001 — Task Ranking

The first ranking implementation is deterministic and read-only.

1. Status group: `in_progress`, `todo`, `blocked`, then `done`.
2. Within each status group: `critical`, `high`, `medium`, then `low`.
3. Earlier valid due dates rank before later dates; missing or invalid dates sort last.
4. Earlier creation timestamps rank first.
5. Task ID is the final stable tie-breaker.

The engine returns copied task dictionaries with a 1-based `rank` and human-readable `ranking_reason`; it does not modify database records. `rank_project_tasks` reads tasks from one existing project and raises `KeyError` for an unknown project.

Date parsing accepts ISO date and timestamp values, normalizes timezone-aware timestamps to UTC, treats naive timestamps as UTC, and safely places invalid values after valid dates.

## Architecture

- Ranking logic: `services/intelligent_task_engine.py`.
- Public service export: `services.IntelligentTaskEngine`.
- Persistence remains in the existing `ProjectRepository`; this checkpoint introduces no schema migration or runtime dependency.
- Focused tests: `tests/test_intelligent_task_engine.py`.

## Verification record

- Feature branch: `feature/phase-07-intelligent-task-engine`.
- GitHub Actions run #118: SUCCESS on commit `e8fa468b12064e9eaeb446bc4fcaf210d4ce4bbe`; Python 3.11.18; `compileall` passed; full suite: 78 passed in 2.27s. [Run #118](https://github.com/glad4u7-crypto/project-continue/actions/runs/44719234814).
- Colab exact-SHA acceptance is pending; the final documentation commit will establish the next verification target.
- Do not mark PC-P07-S001 PASS until focused tests, full test suite, CI, and required runtime verification have been reviewed.
- Do not mark any later Phase 07 checkpoint complete based only on the existence of this ranking implementation.
