# U20-8-02 — Detect and block live SQLite database paths in the test runner

**Timestamp:** 2026-11-28 16:19 Asia/Kolkata  
**Repository:** glad4u7-crypto/project-continue  
**Branch:** phase20/secure-dispatcher-u20-3-01  
**Exact code SHA:** `4b84e390593968af4b14dad6f42377503858db55`  
**Result:** PASS

## Implementation

- Captures the database path configured in the process environment before the pytest fixture replaces it.
- Reads only the `PROJECT_CONTINUE_DB` setting from `.env` and `.env.production`; it does not print or expose other environment values.
- Adds the repository default `.data/project_continue.sqlite3` and the known production path `/var/lib/project-continue/project_continue.sqlite3` to the protected-path set.
- Canonicalizes normal filesystem paths, symlink aliases, and SQLite `file:` URIs before comparing them.
- Rejects the protected database and its `-wal`, `-shm`, and `-journal` sidecar files, including read-only URI access.
- Enforces the check at both `Database.__init__` and the lower-level `sqlite3.connect()` boundary, preventing direct SQLite calls from bypassing the pytest guard.
- Continues to allow pytest `tmp_path`, OS temporary directories, and `:memory:` databases.
- No live database was opened, modified, backed up, restored, or deleted.

## Tests added

- Repository default and known production paths are rejected.
- Direct `sqlite3.connect()` attempts are rejected before SQLite opens the target.
- Read-only `file:...?...mode=ro` URI access is rejected.
- Symlink aliases to protected paths are rejected.
- SQLite WAL/SHM/journal sidecar paths are rejected.
- Temporary file-backed and private in-memory SQLite remain usable.

## Exact-SHA CI evidence

All listed runs checked out exact code SHA `4b84e390593968af4b14dad6f42377503858db55`:

- Main Project Continue CI: [run 46137341188](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137341188) — SUCCESS.
  - Secret scan, dependency audit, compile, production Docker build, Compose validation, production-container smoke test, focused test categories and full regression all passed.
  - Full suite: **434 passed, 11 skipped, 52 subtests passed**.
  - Coverage: **79%**.
  - Test/coverage artifact ID: `15260610503`, SHA-256 digest `0dd894518bd48b44effa8a8d6455531548e3d7c31c0431453aa5f5f9883e7ed5`.
- Fixed-task runner: [run 46137344523](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137344523) — SUCCESS.
- Notebook sandbox acceptance: [run 46137344494](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137344494) — SUCCESS.
- PostgreSQL integration: [run 46137344484](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137344484) — SUCCESS.
- Dashboard browser acceptance: [run 46137344485](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137344485) — SUCCESS.
- Phase 14 operations: [run 46137344492](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137344492) — SUCCESS.
- Phase 13 checkpoint engine: [run 46137344477](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137344477) — SUCCESS.
- Cloud acceptance: [run 46137344473](https://github.com/glad4u7-crypto/project-continue/actions/runs/46137344473) — SUCCESS.

The 11 skips in the main suite are PostgreSQL DSN-gated tests; the dedicated PostgreSQL integration workflow passed independently.

## Preserved failure history

- Earlier exact-head run on `b292ef7aefdb74197b39ffa815880d478a6706c1`, Phase 20 runner run `46137105870`, failed one existing assertion because it expected the old error-message wording. The new guard rejected the path correctly; the assertion was updated to check the rejection rather than a specific message.
- The subsequent exact-head run on `1ca0e50e72d8c45ae2dba89fd0c96218ee29d00b` passed (434 passed, 11 skipped, 52 subtests). The final code then additionally captured `.env.production` and was retested on the final SHA above.
- A separate dashboard-health workflow run `46137340302` ended FAILURE with no job records returned by the GitHub connector. It is not part of the U20-8-02 test suite; the dedicated Dashboard Browser Acceptance run above passed. The empty-job workflow failure is retained as an unresolved auxiliary CI observation, not relabelled PASS.

**Disposition:** U20-8-02 PASS. Next required unit: U20-8-03 — schema version, `integrity_check`, and `foreign_key_check`. PR #71 remains draft and unmerged; `main` and live database state are untouched.
