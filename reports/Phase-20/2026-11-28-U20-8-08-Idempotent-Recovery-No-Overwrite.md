# U20-8-08 — Idempotent recovery and existing-row no-overwrite

**Timestamp:** 2026-11-28 16:19 Asia/Kolkata  
**Repository:** glad4u7-crypto/project-continue  
**Branch:** phase20/secure-dispatcher-u20-3-01  
**Exact code SHA:** `7d111723a365aaa5bca7f884bd52be68f51cb3c4`  
**Result:** PASS

## Implementation

Added `BackupOperations.restore_drill_idempotent(backup_path, destination)`:

- A missing destination is created through the existing rollback-safe restore drill.
- Repeating the same operation against an existing integrity-verified destination with an identical SHA-256 returns the existing path without writing or replacing the file.
- An existing destination with different bytes or failed integrity verification raises `FileExistsError`; it is never overwritten.
- Symlink source/destination and the live database path are rejected.
- The source must be a managed backup and must pass SQLite integrity/foreign-key verification.
- Added operational documentation describing the idempotent no-overwrite contract.
- This helper is for disposable restore drills only; no live or production restore was attempted.

## Tests added

- First restore creates a new destination; repeating the same backup/destination returns the same path and SHA-256.
- Restored project/task identifiers appear exactly once after replay.
- A pre-existing destination containing a conflicting row with the same project ID but a different name is rejected; its SHA-256 and existing row value remain unchanged.
- A live database target remains forbidden.
- All test databases/backups/destinations are pytest temporary fixtures.

## Exact-SHA CI evidence

All listed runs checked out exact code SHA `7d111723a365aaa5bca7f884bd52be68f51cb3c4`:

- Main Project Continue CI: [run 46139905992](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139905992) — SUCCESS.
  - Secret scan, dependency audit, compile, production Docker build, Compose validation, production-container smoke test, focused categories and full regression passed.
  - Full suite: **461 passed, 11 skipped, 52 subtests passed**.
  - Coverage: **80%**.
  - Test/coverage artifact ID: `15261252931`, SHA-256 digest `a9c10a800e24773001621274859cd0996a4c8057e08bdbb503a1566228d0ffd7`.
- Fixed-task runner: [run 46139905997](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139905997) — SUCCESS.
- PostgreSQL integration: [run 46139906005](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139906005) — SUCCESS.
- Notebook sandbox: [run 46139906026](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139906026) — SUCCESS.
- Dashboard browser acceptance: [run 46139905993](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139905993) — SUCCESS.
- Phase 13: [run 46139906015](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139906015) — SUCCESS.
- Phase 14: [run 46139906048](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139906048) — SUCCESS.
- Cloud acceptance: [run 46139906003](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139906003) — SUCCESS.

The 11 skips in the main suite are PostgreSQL DSN-gated tests; the dedicated PostgreSQL integration workflow passed independently.

**Disposition:** U20-8-08 PASS. Next required unit: U20-8-09 — verify Google Drive backup preservation without changing any mount. PR #71 remains draft and unmerged; `main` and live database state are untouched.
