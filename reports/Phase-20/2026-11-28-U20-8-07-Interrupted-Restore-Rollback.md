# U20-8-07 — Interrupted restore and rollback on disposable fixtures

**Timestamp:** 2026-11-28 16:19 Asia/Kolkata  
**Repository:** glad4u7-crypto/project-continue  
**Branch:** phase20/secure-dispatcher-u20-3-01  
**Exact code SHA:** `d914a83bfd0799e869f1bfa7998935533282f9c7`  
**Result:** PASS

## Implementation

- Hardened `BackupOperations.restore_drill()` to track parent directories that did not exist before a restore attempt.
- If copying is interrupted or post-copy integrity verification fails, the operation removes the partial destination database and removes only the newly created parent directories that remain empty.
- Existing directories are not removed. The source backup is not changed. The live database is never a permitted restore target.
- The existing post-copy `Database.verify_backup()` check remains mandatory before a restore drill is reported successful.
- No production restore, live database mutation, or Google Drive operation was performed.

## Fault-injection tests

1. **Interrupted copy:** a disposable source connection is replaced with a fault-injection object whose SQLite `backup()` raises during copy. The test verifies that the partial destination file and newly created empty directory chain are removed, while the source backup and live fixture data remain intact.
2. **Post-copy verification failure:** the verifier is fault-injected to return false after the copy. The restore drill raises a database error and removes the copied destination and newly created empty directories. Source backup and live fixture records remain intact.

All source, backup and destination databases are under pytest `tmp_path`.

## Exact-SHA CI evidence

All listed runs checked out exact code SHA `d914a83bfd0799e869f1bfa7998935533282f9c7`:

- Main Project Continue CI: [run 46139562782](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139562782) — SUCCESS.
  - Secret scan, dependency audit, compile, production Docker build, Compose validation, production-container smoke test, focused categories and full regression passed.
  - Full suite: **458 passed, 11 skipped, 52 subtests passed**.
  - Coverage: **80%**.
  - Test/coverage artifact ID: `15260867392`, SHA-256 digest `b75e64ad28ab006a9c6b9e0d83d024312a405e6fa5ec1dd1345f142c729df3fb`.
- Fixed-task runner: [run 46139562786](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139562786) — SUCCESS.
- PostgreSQL integration: [run 46139562776](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139562776) — SUCCESS.
- Notebook sandbox: [run 46139562810](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139562810) — SUCCESS.
- Phase 14 operations: [run 46139562741](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139562741) — SUCCESS.
- Phase 13 checkpoint engine: [run 46139562737](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139562737) — SUCCESS.

The 11 skips in the main suite are PostgreSQL DSN-gated tests; the dedicated PostgreSQL integration workflow passed independently.

**Disposition:** U20-8-07 PASS. Next required unit: U20-8-08 — idempotent recovery and existing-row no-overwrite test. PR #71 remains draft and unmerged; `main` and live database state are untouched.
