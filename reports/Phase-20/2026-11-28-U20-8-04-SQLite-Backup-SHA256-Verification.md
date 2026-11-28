# U20-8-04 — SQLite backup creation and SHA-256 verification

**Timestamp:** 2026-11-28 16:19 Asia/Kolkata  
**Repository:** glad4u7-crypto/project-continue  
**Branch:** phase20/secure-dispatcher-u20-3-01  
**Exact code SHA:** `db5c1f104781a9f5ae0a49d2a865df64c73126d1`  
**Result:** PASS

## Implementation

Added `database/backup.py` with a bounded-memory SHA-256 and backup-manifest API:

- `sha256_file(path)` streams file bytes in 1 MiB chunks and returns a lowercase SHA-256 digest.
- `verify_backup_checksum(path, expected_sha256)` validates a strict 64-character lowercase hexadecimal digest and compares it with the actual digest using constant-time comparison.
- `create_verified_backup(database, destination)` requires a real `Database` instance, delegates to the existing SQLite online-backup API (which uses exclusive create/no-overwrite), verifies SQLite integrity and foreign-key consistency, then records the backup path, byte size, SHA-256 digest and integrity status in an immutable `BackupManifest`.
- The new API is exported from the `database` package.
- No restore, overwrite, live database access or production backup was performed.

## Tests added

- Creates a disposable SQLite backup containing a fixture row and verifies the manifest's path, byte size and SHA-256 against an independent `hashlib.sha256` calculation.
- Confirms the backup passes `Database.verify_backup` and the fixture row is preserved.
- Confirms checksum verification detects changed bytes.
- Rejects malformed digests and missing files.
- Confirms an existing backup destination is not overwritten.
- Rejects non-`Database` input.

All database and backup files are created under pytest `tmp_path`.

## Exact-SHA CI evidence

All listed runs checked out exact code SHA `db5c1f104781a9f5ae0a49d2a865df64c73126d1`:

- Main Project Continue CI: [run 46137988337](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137988337) — SUCCESS.
  - Secret scan, dependency audit, Python compile, production Docker build, Compose validation, production-container smoke test, focused test categories and full regression passed.
  - Full suite: **444 passed, 11 skipped, 52 subtests passed**.
  - Coverage: **79%**.
  - Test/coverage artifact ID: `15260865271`, SHA-256 digest `17d3c155ef33816c691e684603b62307036b88033eaa918a0cb55e56413cfb52`.
- Fixed-task runner: [run 46137992800](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137992800) — SUCCESS.
- PostgreSQL integration: [run 46137992858](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137992858) — SUCCESS.
- Notebook sandbox: [run 46137992778](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137992778) — SUCCESS.
- Dashboard browser acceptance: [run 46137992773](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137992773) — SUCCESS.
- Phase 13: [run 46137992783](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137992783) — SUCCESS.
- Phase 14: [run 46137992728](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137992728) — SUCCESS.
- Cloud acceptance: [run 46137992867](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137992867) — SUCCESS.

The 11 skips in the main suite are PostgreSQL DSN-gated tests; the dedicated PostgreSQL integration workflow passed independently.

**Disposition:** U20-8-04 PASS. Next required unit: U20-8-05 — backup inventory and restore preview-only report. PR #71 remains draft and unmerged; `main` and live database state are untouched.
