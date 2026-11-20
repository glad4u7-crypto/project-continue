# PC-P04-S002 to PC-P04-S008 — Database Acceptance Specification

**Phase:** 04 — Database System  
**Merged implementation:** PR #10 and PR #12 into main  
**Purpose:** define independently auditable acceptance gates for every database implementation checkpoint.  
**Rule:** implementation is not completion; each checkpoint must be supported by focused tests, CI, runtime evidence where applicable, and a recorded commit.

## PC-P04-S002 — Database Connection

### Scope
Provide short-lived SQLite connections with deterministic cleanup, row access, foreign-key enforcement, busy timeout, health checks, and atomic transaction handling. Both file-backed and documented in-memory operation must work.

### Acceptance criteria
- Parent directories for file-backed database paths are created when needed.
- Every opened connection uses sqlite3.Row.
- PRAGMA foreign_keys is enabled on every connection.
- Busy timeout is applied.
- Connection context always closes the yielded connection.
- Transactions commit on success and roll back on exceptions.
- Timeout values must be positive.
- Shared in-memory state survives across the repository's separate connection contexts and can be explicitly released.

### Evidence mapping
- tests/test_database_connection.py
- File-backed workflow acceptance output.
- Shared in-memory repository regression test.
- GitHub Actions compile/test job.

## PC-P04-S003 — Project Table

### Scope
Persist projects with stable identifiers, unique names, descriptions, lifecycle status, and timestamps.

### Acceptance criteria
- Schema contains project primary key, unique name (validated by repository), status constraint, and timestamps.
- Create, read, list, update, and delete operations behave deterministically.
- Missing project updates and invalid status values are rejected.
- Project deletion cascades to project-owned tasks and activity records.
- Project data survives closing and reopening database connections.

### Evidence mapping
- tests/test_database_repository.py::test_project_and_task_crud
- tests/test_database_repository.py::test_delete_project_cascades_related_records
- Real SQLite file-backed workflow acceptance output.

## PC-P04-S004 — Task Table

### Scope
Persist project-owned tasks with title, description, priority, status, optional due date, and timestamps.

### Acceptance criteria
- Every task references an existing project.
- Priority and status are constrained to supported values.
- Repository create, read, list, update, and delete operations are covered.
- Invalid or missing project ownership is rejected.
- Project deletion cascades to tasks.
- Task deletion removes dependency edges and preserves activity history with a null task reference.
- Task data survives closing and reopening database connections.

### Evidence mapping
- tests/test_database_repository.py::test_project_and_task_crud
- tests/test_database_repository.py::test_foreign_keys_and_dependency_constraints
- Real SQLite file-backed workflow acceptance output.

## PC-P04-S005 — Dependency Table

### Scope
Represent directed task dependencies and prevent invalid ownership and cycles.

### Acceptance criteria
- Both endpoints must reference existing tasks.
- A task cannot depend on itself.
- Dependency endpoints must belong to the same project.
- Repository operations reject missing endpoints, cross-project edges, duplicate edges, and cycles.
- SQLite INSERT and UPDATE triggers enforce same-project ownership even when repository validation is bypassed.
- SQLite INSERT and UPDATE triggers reject cycles even when repository validation is bypassed.
- Deleting a task removes dependency edges.

### Evidence mapping
- tests/test_database_repository.py::test_foreign_keys_and_dependency_constraints
- tests/test_database_repository.py::test_dependencies_cannot_cross_projects
- tests/test_database_repository.py::test_database_triggers_enforce_dependency_integrity_on_update
- tests/test_database_repository.py::test_database_triggers_reject_dependency_cycles_on_insert_and_update
- Real SQLite file-backed workflow acceptance output.

## PC-P04-S006 — Activity History

### Scope
Persist project activity events with optional task association and JSON payloads.

### Acceptance criteria
- Each event references an existing project.
- Optional task reference must belong to the same project.
- Same-project ownership is enforced by repository validation and SQLite INSERT/UPDATE triggers.
- JSON payload round-trips as structured data.
- Events are returned in deterministic newest-first order with a bounded limit.
- Deleting a task preserves its event and clears task association.
- Deleting a project cascades to its activity events.

### Evidence mapping
- tests/test_database_repository.py::test_activity_history_records_json_payload
- tests/test_database_repository.py::test_activity_task_must_belong_to_same_project
- tests/test_database_repository.py::test_database_trigger_rejects_cross_project_activity_insert_and_update
- Real SQLite file-backed workflow acceptance output.

## PC-P04-S007 — Database CRUD

### Scope
Expose validated repository operations for projects, tasks, dependencies, and activity history.

### Acceptance criteria
- CRUD behavior is transactionally safe.
- Identifiers and domain fields use core validators.
- Missing records and invalid values fail explicitly.
- SQL values are parameterized.
- Dependency and activity ownership rules are enforced.
- Reopening the database preserves committed records.
- Delete/cascade behavior does not damage unrelated projects.

### Evidence mapping
- database/repository.py
- tests/test_database_repository.py
- Real SQLite file-backed workflow acceptance output.

## PC-P04-S008 — Database Tests

### Scope
Maintain automated tests for connection behavior, schema constraints, repository behavior, rejection paths, and regressions.

### Acceptance criteria
- Focused database test suite passes.
- Full project test suite passes.
- GitHub Actions compile and test job passes on the exact PR head commit.
- Colab runtime tests pass on the exact PR head commit.
- File-backed workflow acceptance passes.
- New integrity rules have explicit regression tests.
- Evidence records exact commit SHA, commands, counts, and results.

### Evidence mapping
- tests/test_database_connection.py
- tests/test_database_repository.py
- .github/workflows/ci.yml
- Colab output and PR workflow run.

## Current audit status — 2026-11-20

- S001: SQLite decision recorded in PC-P04-S001-DATABASE-SELECTION.md.
- S002-S008: implementation exists; this specification makes the acceptance criteria traceable checkpoint-by-checkpoint.
- Audit found and fixed additional SQLite-level gaps on the working branch: dependency ownership and cycle checks on INSERT/UPDATE, plus shared in-memory persistence across short-lived connections.
- Regression tests have been added for those fixes. The updated focused suite is expected to contain 15 tests and the full suite 41 tests; these counts are targets until rerun output confirms them.
- Previous 12/12 focused, 38/38 full-suite, 10/10 file-backed workflow, and CI run #73 results apply to the earlier code commit only. They do not verify the latest audit fixes.
- PR #12 merged at 44166feafc7af16ad7b3358dd186c7cd68c1421d. Main CI run #270 passed: database marker group 21 passed; full suite 161 passed; statement coverage 95%; Gitleaks and pip-audit passed. Final Colab rerun is still pending.
- The Streamlit UI is outside the current database-persistence checkpoint scope; this specification does not claim a completed user-facing project/task workflow.


## Current verification record — 2026-11-20

- PR #10 and PR #12 are merged into main.
- Main CI run #270: SUCCESS; Python 3.11.18; Gitleaks no leaks; pip-audit no known vulnerabilities; compile passed.
- Focused groups: unit 68, integration 28, API 21, database 21 passed.
- Full suite: 161 passed; statement coverage 95% (821 statements; 39 uncovered).
- Colab exact-SHA retest and real file-backed workflow verification remain required for final Phase 04 acceptance.
