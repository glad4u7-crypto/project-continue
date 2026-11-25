# PostgreSQL adapter — implementation status

Branch: `feature/postgresql-database-adapter`

## Implemented foundation

- Added `database/postgres_connection.py` with psycopg 3 connection creation,
  dictionary rows, bounded connection timeout, short-lived connection context,
  explicit transaction context, and a read-only `SELECT 1` health check.
- Added `psycopg[binary]>=3.2,<4` to runtime dependencies.
- Added isolated constructor/validation tests.


- Added `database/postgres_schema.py` with a separate idempotent initial schema
  for projects, tasks, dependencies, activity, users, memberships, audit events,
  and login attempts. PostgreSQL trigger guards preserve dependency-cycle,
  same-project activity/dependency, and immutable-audit invariants.
- Added static schema coverage tests in `tests/test_postgres_schema.py`.

## Verification status

The branch has been reviewed through GitHub file retrieval and commit comparison.
No PostgreSQL server/DSN is configured in this task, so neither a live schema
initialization nor PostgreSQL integration tests have been run. Static tests
have been added but are not represented as passing until executed in CI or an
isolated test environment.

## Deliberate safety boundary

This is **not yet a drop-in replacement** for the current SQLite `Database`.
The current `ProjectRepository`, `AccessControl`, schema migrations, and
backup/restore code use SQLite-specific SQL and behavior, including
`PRAGMA`, `executescript`, `INSERT OR IGNORE`, `AUTOINCREMENT`,
SQLite triggers, qmark parameters, and `lastrowid`.

Do not select `PostgresDatabase` in `database/runtime.py`, point production
traffic at it, or migrate user data until the compatibility layer, PostgreSQL
schema/migrations, access-control schema, backup strategy, and full acceptance
suite are implemented and verified.

## Remaining implementation gates

1. Define a small backend protocol and SQL dialect boundary.
2. Port repository SQL and schema to PostgreSQL, preserving constraints and
   recursive dependency-cycle protections.
3. Port identity, session, membership, and immutable audit tables/triggers.
4. Add backend selection using an explicit secret/URL; never infer a provider
   from unrelated secret names.
5. Add PostgreSQL integration tests against an isolated disposable database.
6. Implement a verified, repeatable SQLite-to-PostgreSQL migration with row
   counts, foreign-key checks, checksums, and rollback/restore rehearsal.
7. Run the complete regression and acceptance suite before any deployment.

No production database, Streamlit configuration, Colab runtime, Drive database,
existing dashboard, or backup directory is changed by this branch.
