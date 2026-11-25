# PostgreSQL adapter — implementation status

Merged into `main` by PR #44: `510d90d8f7981f18d0957cf646db62f117f84ed0` (2026-11-25)

## Implemented foundation

- PostgreSQL connection and transaction primitives using psycopg 3.
- Separate PostgreSQL schema, schema version parity (version 2), repository, and PostgreSQL access-control implementation.
- PostgreSQL trigger guards for same-project dependencies/activity, dependency-cycle prevention, and immutable audit events.
- Explicit SQLite-to-PostgreSQL migration utility. Its default is read-only; real migration requires `dry_run=False`, an empty dedicated PostgreSQL target, and performs transactional row-count and SHA-256 verification for all configured tables.
- Custom-format PostgreSQL backup with sidecar metadata, byte-count and SHA-256 validation, archive-list validation, and restore refusal for a non-empty target.
- Dedicated PostgreSQL 16 GitHub Actions workflow with isolated integration, migration, backup, restore, and migration-rollback test databases.

## Part 1 — Database Foundation runtime work

PR #53 adds explicit runtime backend selection for controlled non-production validation:

- SQLite remains the default when `PROJECT_CONTINUE_DB_BACKEND` is unset.
- PostgreSQL requires an explicit DSN and selects the PostgreSQL repository and access-control adapters.
- PostgreSQL production selection is deliberately blocked until application-service and dashboard acceptance are complete.
- Runtime selection never runs migration or copies data.
- Migration now has a dedicated failure-injection acceptance test proving that checksum verification failure rolls back all copied target rows.

## Verified CI evidence

The PR #53 head must pass the Project Continue CI, PostgreSQL integration, and acceptance workflows before this foundation is considered accepted. CI results are linked from PR #53; do not treat a prior commit's green checks as evidence for a later head commit.

## Remaining acceptance boundaries

- The migration and rollback CI tests use generated disposable SQLite fixtures and isolated disposable PostgreSQL targets. They do not migrate the user's live Drive database.
- The backup/restore round-trip uses dedicated disposable PostgreSQL databases. It does not validate a production backup or restore.
- Repository CRUD and PostgreSQL access-control integration tests do not constitute full compatibility acceptance for every application service.
- Project Service, Task Service, Authentication Service, Memory, Checkpoint, and Automation service compatibility remain a separate application-service acceptance phase.
- Dashboard acceptance against the currently running Streamlit instance and production readiness have not been completed.
- No production database switch or user-data migration has been performed.

## Safety boundary

Do not select PostgreSQL in production runtime or migrate user data until application-service compatibility, secrets/configuration, full security acceptance, dashboard acceptance, production backup/restore policy, and explicit operator approval are complete.

No production database, Streamlit configuration, Colab runtime, Drive database, existing dashboard, or existing backup directory is changed by the feature branch CI.


## Part 1 — Application Service Compatibility (CI acceptance passed)

The stacked feature branch `feature/part-1-application-service-compatibility` adds a PostgreSQL connection compatibility layer for existing application services:

- Translates the existing service-layer SQLite `?` bind markers to PostgreSQL `%s` markers while preserving native PostgreSQL statements.
- Supports the simple semicolon-delimited DDL scripts used by Memory/Checkpoint and Automation services.
- Normalizes PostgreSQL integrity exceptions to the service layer's existing integrity-error contract.
- Adds live PostgreSQL acceptance for Project Service, Task Service, Authentication/Authorization Service, Memory/Checkpoint Service, and Automation Service.
- The tests use a dedicated disposable PostgreSQL CI database. They do not connect to the user's production database.

Acceptance passed on exact head SHA 5a1b711440edb0888c783775a0c7513155b2883f: PostgreSQL 16 integration (268 passed), Cloud Acceptance Lab (Python 3.11 and 3.13 passed), Project Continue CI (258 passed, 10 environment-gated PostgreSQL tests skipped in the non-PostgreSQL CI runner), and Phase 14 Production Operations (Python 3.11 and 3.13 passed). The PostgreSQL integration job runs the 268-test suite against disposable PostgreSQL 16 and includes the four new application-service acceptance tests. This work does not enable production PostgreSQL selection or change the running dashboard.
