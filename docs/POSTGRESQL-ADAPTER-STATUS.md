# PostgreSQL adapter — implementation status

Branch: `feature/postgresql-database-adapter`
Merged into `main` by PR #44: `510d90d8f7981f18d0957cf646db62f117f84ed0` (2026-11-25)

## Implemented foundation

- PostgreSQL connection and transaction primitives using psycopg 3.
- Separate PostgreSQL schema, schema version parity (version 2), repository, and PostgreSQL access-control implementation.
- PostgreSQL trigger guards for same-project dependencies/activity, dependency-cycle prevention, and immutable audit events.
- Explicit SQLite-to-PostgreSQL migration utility. Its default is read-only; real migration requires `dry_run=False`, an empty dedicated PostgreSQL target, and performs transactional row-count and SHA-256 verification for all configured tables.
- Custom-format PostgreSQL backup with sidecar metadata, byte-count and SHA-256 validation, archive-list validation, and restore refusal for a non-empty target.
- Dedicated PostgreSQL 16 GitHub Actions workflow with separate integration, migration, backup, and restore test databases.

## Verified CI evidence (2026-11-25)

The adapter and migration tooling are now merged into `main` as optional infrastructure. The application runtime remains on SQLite; this merge did not select PostgreSQL as the production database or migrate any user data.

- PostgreSQL integration workflow run #33, commit `3ce427eef53630e65eb9eeb5c0570cdb36c4ee3b`: **252 passed**. The job provisioned PostgreSQL 16 and configured separate DSNs for general integration, migration, backup, and restore tests. The full regression and PostgreSQL integration suite completed successfully.
- Project Continue CI run #540 on the same commit: **248 passed, 4 skipped**. The four skips are expected in this general workflow because it does not configure the dedicated PostgreSQL test DSNs; the PostgreSQL-specific workflow above does.
- Cloud Acceptance Lab #92: successful on the same commit, Python 3.11 and 3.13.
- Phase 13 run #84 and Phase 14 run #80: successful on the same commit.
- The previous PostgreSQL restore failure caused by client/server major-version mismatch was addressed by pinning the backup helper to PostgreSQL 16 client binaries through `PG_CLIENT_MAJOR=16`.

## Remaining acceptance boundaries

- The CI migration test uses a generated disposable SQLite fixture and a dedicated disposable PostgreSQL target. It does not migrate the user's live Drive database.
- The CI backup/restore round-trip uses dedicated disposable PostgreSQL databases. It does not validate a production backup or restore.
- PostgreSQL access-control coverage in the general suite is not equivalent to a full live security acceptance across real application users and roles.
- The running application still initializes `database/runtime.py` with the SQLite `Database` and `ProjectRepository`. The PostgreSQL adapter is not yet a drop-in runtime replacement.
- Dashboard acceptance against the currently running Streamlit instance and production readiness have not been completed.
- PR #44 was merged after the PostgreSQL 16 integration and full regression workflow passed. The merge adds optional adapter/migration/backup tooling only; no production database switch has been performed.

## Safety boundary

Do not select PostgreSQL in production runtime or migrate user data until runtime compatibility, secrets/configuration, full security acceptance, dashboard acceptance, production backup/restore policy, and explicit operator approval are complete.

No production database, Streamlit configuration, Colab runtime, Drive database, existing dashboard, or existing backup directory is changed by the feature branch CI.
