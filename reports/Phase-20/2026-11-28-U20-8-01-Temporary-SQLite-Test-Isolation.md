# U20-8-01 — Temporary SQLite databases mandatory in automated tests

**Date:** 2026-11-28 (Asia/Kolkata)  
**Branch:** phase20/secure-dispatcher-u20-3-01  
**Exact code/test SHA:** b00d705981d0a2ff1446917a6552bb031d08fb07  
**Full CI:** [Run 46130732459](https://github.com/glad4u7-crypto/project-continue/actions/runs/46130732459) — SUCCESS

## Implemented

- Added tests/conftest.py with an autouse fixture applied to every pytest test.
- Before importing application settings, the test process establishes a temporary session database root and forces APP_ENV=test, SQLite backend and a temporary default database path.
- For each test, the fixture sets PROJECT_CONTINUE_DB to that test's pytest tmp_path and refreshes config.settings from the isolated environment.
- Database.__init__ is guarded: file-backed SQLite paths must resolve beneath pytest tmp_path, the OS temporary directory (for existing tempfile.TemporaryDirectory-based tests), or the temporary pytest-session root. The private :memory: mode is also allowed.
- Repository/default .data paths and production /var/lib paths are rejected before SQLite opens or creates a file.
- Per-test Streamlit repository caches are cleared so a cached database handle cannot bypass the current test's isolated path.
- The temporary session root is removed at pytest session end.
- Added tests/test_database_test_isolation.py to prove tmp_path, tempfile.TemporaryDirectory and :memory: are accepted, while repository/default and production paths are rejected.

## Exact-SHA evidence

Full CI run 46130732459 checked out b00d705981d0a2ff1446917a6552bb031d08fb07:
- Secret scan: PASS.
- Dependency audit: PASS.
- Python compile: PASS.
- Production Docker build: PASS.
- Compose validation: PASS.
- Production-container smoke test: PASS.
- Focused test categories: PASS.
- Full suite: **431 passed, 11 skipped, 52 subtests passed**.
- The 11 skips are PostgreSQL DSN-gated integration tests; no SQLite tests were skipped by the isolation guard.
- Test/coverage reports uploaded by CI.

## Safety boundary

This checkpoint uses only temporary SQLite files or private in-memory SQLite. No repository .data database, production database, live PostgreSQL service or Google Drive database was opened or modified.

**Disposition:** U20-8-01 PASS. U20-8-02..10 remain NOT STARTED. PR #71 remains draft/unmerged; main is unchanged.
