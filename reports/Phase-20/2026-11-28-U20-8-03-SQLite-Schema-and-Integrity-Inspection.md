# U20-8-03 — SQLite schema version and integrity checks

**Timestamp:** 2026-11-28 16:19 Asia/Kolkata  
**Repository:** glad4u7-crypto/project-continue  
**Branch:** phase20/secure-dispatcher-u20-3-01  
**Exact code SHA:** `91ba72a3dabc4b77f7f2e9bf374f8fed6369cccd`  
**Result:** PASS

## Implementation

Added `database/diagnostics.py` with a read-only `inspect_sqlite_database(path)` diagnostic and typed immutable result objects:

- Reads the persisted `schema_version` row and compares it with the application `SCHEMA_VERSION`.
- Runs `PRAGMA integrity_check` and records every returned result.
- Runs `PRAGMA foreign_key_check` and records table, rowid, parent table and foreign-key index for each violation.
- Reports a database healthy only when the schema version is supported, integrity_check returns exactly `ok`, and no foreign-key violations exist.
- Opens existing files using SQLite `mode=ro`; it does not create missing files, migrate schemas, or mutate application records.
- Exports `SQLiteIntegrityReport`, `ForeignKeyViolation`, and `inspect_sqlite_database` from the database package.

## Tests added

- Healthy initialized database: expected schema version, integrity `ok`, no foreign-key violations.
- Read-only behavior: SHA-256 of the database file is unchanged before and after inspection.
- Missing schema-version table: reports unsupported/uninitialized without migrating.
- Newer unsupported schema version: reports unhealthy.
- Deliberately inserted orphan row in a disposable tmp_path database: integrity_check remains `ok`, while foreign_key_check reports the exact violation.
- Missing database path: raises `FileNotFoundError` and does not create a file.

All fixtures are disposable pytest temporary databases. No production or live database was accessed.

## Exact-SHA evidence

All listed runs checked out exact code SHA `91ba72a3dabc4b77f7f2e9bf374f8fed6369cccd`:

- Main Project Continue CI: [run 46137675625](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137675625) — SUCCESS.
  - Secret scan, dependency audit, Python compile, production Docker build, Compose validation, container smoke test, focused test categories and full regression passed.
  - Full suite: **439 passed, 11 skipped, 52 subtests passed**.
  - Coverage: **79%**.
  - Test/coverage artifact ID: `15260616141`, SHA-256 digest `7149ccc9e1f02a4aef87c25f839050aa4d5b2cf6dd02f2d2289d0857f71cd487`.
- Fixed-task runner: [run 46137678458](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137678458) — SUCCESS.
- Notebook sandbox: [run 46137678452](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137678452) — SUCCESS.
- PostgreSQL integration: [run 46137678446](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137678446) — SUCCESS.
- Dashboard browser acceptance: [run 46137678453](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137678453) — SUCCESS.
- Phase 13: [run 46137678448](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137678448) — SUCCESS.
- Phase 14: [run 46137678462](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137678462) — SUCCESS.
- Cloud acceptance: [run 46137678565](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137678565) — SUCCESS.

The 11 skips in the main suite are PostgreSQL DSN-gated tests; the dedicated PostgreSQL integration workflow passed independently.

**Disposition:** U20-8-03 PASS. Next required unit: U20-8-04 — backup creation and SHA-256 checksum verification. PR #71 remains draft and unmerged; `main` and live database state are untouched.
