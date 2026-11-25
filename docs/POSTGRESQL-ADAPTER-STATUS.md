# PostgreSQL adapter — implementation status

Branch: `feature/postgresql-database-adapter`

## Implemented foundation

- Added `database/postgres_connection.py` with psycopg 3 connection creation,
  dictionary rows, bounded connection timeout, short-lived connection context,
  explicit transaction context, and a read-only `SELECT 1` health check.
- Added `psycopg[binary]>=3.2,<4` to runtime dependencies.
- Added `database/postgres_schema.py` with a separate idempotent schema for
  projects, tasks, dependencies, activity, users, memberships, audit events,
  and login attempts.
- PostgreSQL schema version is now explicitly aligned with SQLite
  `SCHEMA_VERSION = 2`; a regression test checks this parity.
- PostgreSQL trigger guards enforce same-project dependencies/activity,
  dependency-cycle prevention, and immutable audit events.
- Added `database/postgres_repository.py` for the project/task repository
  surface, including PostgreSQL placeholders, transactions, recursive
  dependency checks, and `RETURNING id`.
- Added `services/postgres_access_control.py` for password hashing,
  login throttling, signed sessions, project membership checks, and audit
  writes using PostgreSQL SQL.
- Updated the authorization policy/context to accept the PostgreSQL adapter
  without changing the runtime database selection.
- Added static contract tests and opt-in live tests in
  `tests/test_postgres_integration.py`. Live tests require
  `TEST_POSTGRES_DSN` and use a dedicated disposable PostgreSQL database.
- Added `.github/workflows/postgres-integration.yml`, which provisions
  PostgreSQL 16 and runs the complete pytest suite on pushes to main/this
  feature branch and pull requests targeting main.

## Verification status

The code and test workflow have been committed to this feature branch.
The live integration tests have **not** been reported as passing until the
GitHub Actions run completes successfully. When run without
`TEST_POSTGRES_DSN`, live database tests skip explicitly; they never fall
back to the application's SQLite database.

## Deliberate safety boundary

This is **not yet a drop-in replacement** for the current SQLite
`Database`. The running application still initializes
`database/runtime.py` with the SQLite `Database` and
`ProjectRepository`. Do not select `PostgresDatabase` in runtime, point
production traffic at it, or migrate user data until compatibility, migration,
backup/restore, and full acceptance gates are implemented and verified.

No production database, Streamlit configuration, Colab runtime, Drive
database, existing dashboard, or backup directory is changed by this branch.

## Remaining implementation gates

1. Complete and test the PostgreSQL migration path for all SQLite tables and
   current schema versions, including row counts, foreign-key checks,
   checksums, and rollback/restore rehearsal.
2. Run the new PostgreSQL service-backed GitHub Actions workflow and fix any
   failures; verify the full existing regression suite as well as live tests.
3. Add operational backup/restore and connection-secret configuration with
   explicit opt-in selection, without inferring a database provider from
   unrelated secret names.
4. Run full acceptance before any production switch.
