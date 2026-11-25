# Phase 17 — PostgreSQL runtime compatibility

## Objective

Make PostgreSQL a supported, explicitly selected application backend without changing the existing SQLite default or touching any live database. This phase is an application compatibility project, not merely a DSN/configuration change.

## Baseline confirmed on 2026-11-25

- Base `main` commit: `095ab7d64c56e472196b887ef0414241b4307eef`.
- PR #44 already merged the optional PostgreSQL 16 connection, schema, project/task repository, access-control adapter, migration utility, backup/restore helpers, and dedicated integration workflow.
- `database/runtime.py` still constructs `Database` and `ProjectRepository` (SQLite) unconditionally.
- `config.py` exposes `PROJECT_CONTINUE_DB` as a filesystem path; it has no explicit backend selector or PostgreSQL DSN setting.
- `ui/authentication.py` constructs SQLite `AccessControl` directly from the runtime repository database.
- `services/automation_engine.py` creates its own tables with SQLite DDL/placeholders and catches `sqlite3.IntegrityError`.
- `services/memory_checkpoint_engine.py` and other feature services use the shared database connection directly; each must be audited for SQLite-only SQL and schema initialization.
- PostgreSQL's repository currently covers project/task/dependency/activity operations. Its interface parity with all service/UI call sites is not yet established.
- Existing PostgreSQL CI proves adapter/migration/backup behavior against disposable PostgreSQL 16 databases. It does not prove that the full Streamlit application can run on PostgreSQL.

## Compatibility workstreams

1. **Configuration and runtime selection**
   - Add an explicit backend setting with SQLite as the unchanged default.
   - Accept a PostgreSQL DSN only through environment/host secrets; never log or display it.
   - Cache one backend/repository resource per normalized backend identity without exposing credentials in cache keys or diagnostics.
   - Fail closed on invalid/missing PostgreSQL configuration; never silently fall back to SQLite.

2. **Repository contract**
   - Define the complete repository contract used by services and UI.
   - Compare SQLite and PostgreSQL implementations method-by-method and behavior-by-behavior.
   - Add missing PostgreSQL operations before runtime selection is enabled.
   - Preserve transaction boundaries, row shapes, ordering, error semantics, dependency rules, and activity history.

3. **Authentication and authorization**
   - Select the matching AccessControl adapter from the same runtime backend.
   - Verify account provisioning, login throttling, password verification, signed-session issue/verify/expiry, role checks, membership checks, and audit events on PostgreSQL.
   - Confirm authorization is enforced at service boundaries, not only by Streamlit visibility.

4. **Memory and checkpoints**
   - Audit every table, query, placeholder, upsert, generated identifier, JSON field, and transaction in the memory/checkpoint engine.
   - Implement backend-neutral persistence or explicit PostgreSQL equivalents.
   - Preserve project scoping, snapshot hashes, immutable history, preview-first recovery, and additive-only restore behavior.

5. **Automation**
   - Port rules, schedules, runs, notifications, deduplication, retries, and claims to PostgreSQL.
   - Use concurrency-safe schedule claiming and preserve bounded retries.
   - Replace SQLite-specific integrity exception handling with backend-neutral handling.

6. **Acceptance and operations**
   - Run existing SQLite regression unchanged.
   - Run PostgreSQL 16 integration plus full application/service tests against disposable databases.
   - Add two-backend contract tests and real-browser acceptance against a disposable PostgreSQL-backed instance.
   - Verify secret redaction, health diagnostics, backup/restore, and migration rehearsal using synthetic data only.

## Required release gates

- SQLite remains the default and its existing data is not migrated or modified by CI.
- PostgreSQL runtime is opt-in and cannot be activated without an explicit DSN.
- No automatic migration, destructive schema reset, database drop, or restore over a non-empty target.
- All relevant tests pass independently on SQLite and PostgreSQL 16.
- Authentication, project authorization, memory/checkpoints, and automation pass PostgreSQL acceptance.
- Browser acceptance and backup/restore rehearsal pass before any production deployment.
- Production selection or migration of user data requires a separate explicit operator decision.

## Immediate next implementation sequence

1. Complete a call-site inventory for every direct database access in `ui/`, `services/`, `scripts/`, and startup code.
2. Publish a repository/service compatibility matrix and close the missing-method/SQLite-SQL gaps.
3. Implement backend-neutral runtime construction behind an explicit configuration flag, initially with tests only.
4. Integrate auth, memory/checkpoints, and automation in separate reviewable commits.
5. Run dual-backend acceptance and prepare a deployment handoff; do not deploy or migrate during this phase's CI work.

## Safety boundary

This branch is based on the verified `main` commit above. It does not modify `main`, merge PRs #51/#52, access or alter the running dashboard, restart Colab/Streamlit, access Google Drive backups, or migrate any live SQLite/PostgreSQL database. All database integration tests must use disposable fixtures and isolated CI databases.

## Initial call-site audit (2026-11-25)

| Area | Current coupling found | Required Phase 17 action |
|---|---|---|
| Runtime | `database/runtime.py` hardcodes SQLite `Database` + `ProjectRepository` | Explicit backend factory and safe cache identity |
| Project/task repository | Separate `PostgresProjectRepository` exists; SQLite services/UI import SQLite exception types | Complete interface parity and backend-neutral error handling |
| Authentication | `PostgresAccessControl` exists, but `ui/authentication.py` imports/constructs SQLite `AccessControl` | Runtime-selected access-control adapter and full session/security tests |
| Authorization context | Contains a PostgreSQL placeholder branch for principal lookup | Verify all policy operations against both adapters |
| Project/task services | `services/project_management.py`, `services/task_management.py` import `sqlite3` and the concrete SQLite repository | Remove concrete adapter assumptions; preserve duplicate/not-found semantics |
| Project management UI | `ui/project_management.py` imports `sqlite3` and catches `sqlite3.IntegrityError` | Catch stable service/domain errors rather than driver-specific exceptions |
| Memory/checkpoints | `services/memory_checkpoint_engine.py` initializes tables through `executescript` and uses SQLite-oriented persistence | Extract schema initialization and port SQL/transaction behavior |
| Automation | `services/automation_engine.py` uses `executescript`, SQLite placeholders and `sqlite3.IntegrityError` | Port schema, idempotency, retries, and concurrency-safe schedule claims |
| Operations | SQLite backup operations are wired separately from PostgreSQL backup helpers | Backend-aware, non-destructive backup/restore runbooks and tests |

### Implementation ordering decision

Do not change `database/runtime.py` to select PostgreSQL yet. The runtime switch would route authentication, memory/checkpoint, automation, and UI code into SQLite-specific SQL paths. First introduce a stable service-facing contract and remove the driver-specific assumptions in small, independently tested slices. Only then enable explicit PostgreSQL runtime selection.
