# U20-8-08 — Idempotent recovery and existing-row no-overwrite

**Timestamp:** 2026-11-28 16:58 Asia/Kolkata  
**Repository:** glad4u7-crypto/project-continue  
**Branch:** phase20/secure-dispatcher-u20-3-01  
**Exact tested SHA:** `7d111723a365aaa5bca7f884bd52be68f51cb3c4`  
**Result:** PASS

## Implementation

The existing `BackupOperations.restore_drill_idempotent(backup, destination)` implementation was reviewed and exercised; no duplicate implementation was added.

- First restore creates the destination from a verified managed backup.
- Repeating the same request against an existing integrity-verified destination with the same SHA-256 returns the existing path without writing or replacing the file.
- If the destination is invalid or contains different bytes/data, the operation raises `FileExistsError`; it does not overwrite the existing file.
- Symlink source/destination and the live database path are rejected.
- All source, backup, destination and existing-row databases are disposable pytest `tmp_path` fixtures.

## Focused acceptance tests

1. **Idempotent replay:** restore the same backup twice; both calls return the same path and destination SHA-256 remains identical. The reopened DB contains exactly the expected single project and task, with no duplicate rows.
2. **Existing-row no-overwrite:** create an independent destination DB containing the same project ID but a different row value. Restore raises `FileExistsError`; destination SHA-256 and existing row value remain unchanged.
3. **Live target guard:** targeting the live fixture DB raises `ValueError`; the source backup remains valid.

## Exact-SHA CI evidence

All listed runs checked out `7d111723a365aaa5bca7f884bd52be68f51cb3c4`:

- Main Project Continue CI: [run 46139905992](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139905992) — SUCCESS.
  - Secret scan, dependency audit, compile, production container build, Compose validation, smoke test, focused categories and full regression all passed.
  - Full suite: **461 passed, 11 skipped, 52 subtests passed**; coverage **80%**.
  - Test/coverage artifact ID `15261252931`, 337,634 bytes, SHA-256 `a9c10a800e24773001621274859cd0996a4c8057e08bdbb503a1566228d0ffd7`.
- Duplicate PR-triggered main CI: [run 46139903094](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139903094) — SUCCESS.
- Fixed-task runner: [run 46139905997](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139905997) — SUCCESS.
- PostgreSQL integration: [run 46139906005](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139906005) — SUCCESS.
- Notebook sandbox: [run 46139906026](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139906026) — SUCCESS.
- Dashboard browser acceptance: [run 46139905993](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139905993) — SUCCESS.
- Cloud Acceptance Lab: [run 46139906003](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139906003) — SUCCESS.
- Phase 13: [run 46139906015](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139906015) — SUCCESS.
- Phase 14: [run 46139906048](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139906048) — SUCCESS.

The 11 main-suite skips are opt-in PostgreSQL DSN-gated tests; the dedicated PostgreSQL workflow passed. The separate dashboard-health workflow [run 46139902151](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139902151) failed on this SHA and remains preserved in Actions history. It is an operational health check, not a passing result and not counted as a SQLite recovery test; browser acceptance independently passed.

## Safety and disposition

No production database, live restore target, Google Drive mount/backup, deployment, or live service was touched. No file was deleted or overwritten. PR #71 remains draft and unmerged; `main` remains unchanged.

**Disposition:** U20-8-08 PASS. Next required unit: U20-8-09 — Google Drive backup preservation verification without changing any mount.
