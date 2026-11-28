# U20-8-06 — Reject corrupt and truncated SQLite backups

**Timestamp:** 2026-11-28 16:19 Asia/Kolkata  
**Repository:** glad4u7-crypto/project-continue  
**Branch:** phase20/secure-dispatcher-u20-3-01  
**Exact code SHA:** `692c124cc388663485e2c7010e84b8b23bf5d29d`  
**Result:** PASS

## Implementation

- Hardened `Database.verify_backup(path)` to reject zero-byte files explicitly. SQLite otherwise treats a zero-byte file as an empty valid database, which is not an acceptable backup artifact.
- The verifier now returns `False` for corrupt SQLite files and `PRAGMA integrity_check` / `foreign_key_check` database errors, while preserving `FileNotFoundError` for a missing path.
- Hardened `BackupOperations.inventory_backups()` to retain the SHA-256 metadata but report a failed integrity check as a sanitized `DatabaseError` status rather than leaving an empty error field.
- Restore preview remains read-only and marks corrupt, zero-byte, truncated, checksum-mismatched, or unsupported-schema files ineligible.

## Tests added

- Valid application backup remains verifiable.
- Arbitrary non-SQLite bytes are rejected.
- Zero-byte backup is rejected.
- A valid application backup truncated to half its byte length is rejected.
- Restore preview rejects corrupt, zero-byte and truncated files even when the caller supplies the matching SHA-256 of those damaged bytes.
- Inventory reports integrity failures with an error type and never marks them eligible.
- All test files are disposable pytest temporary files; no live or production backup was accessed.

## Exact-SHA CI evidence

All listed runs checked out exact code SHA `692c124cc388663485e2c7010e84b8b23bf5d29d`:

- Main Project Continue CI: [run 46139127323](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139127323) — SUCCESS.
  - Secret scan, dependency audit, compile, production Docker build, Compose validation, container smoke test, focused test categories and full regression passed.
  - Full suite: **456 passed, 11 skipped, 52 subtests passed**.
  - Coverage: **80%**.
  - Test/coverage artifact ID: `15261490771`, SHA-256 digest `b6df59f0e2fad02ead6cac9d882f5e4b1ccce8ba7d751aca49b93705b23d8be2`.
- Fixed-task runner: [run 46139132269](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139132269) — SUCCESS.
- PostgreSQL integration: [run 46139132302](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139132302) — SUCCESS.
- Notebook sandbox: [run 46139132276](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139132276) — SUCCESS.
- Dashboard browser acceptance: [run 46139132185](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139132185) — SUCCESS.
- Phase 13: [run 46139132237](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139132237) — SUCCESS.
- Phase 14: [run 46139132310](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139132310) — SUCCESS.
- Cloud acceptance: [run 46139132180](https://github.com/glad4u7-crypto/project-continue/actions/runs/46139132180) — SUCCESS.

The 11 skips in the main suite are PostgreSQL DSN-gated tests; the dedicated PostgreSQL integration workflow passed independently.

## Preserved failure history

- Run `46138403534` exposed a fixture that placed the source DB inside the backup inventory directory; the fixture was corrected.
- Run `46138508739` exposed an unmanaged restore-preview fixture that did not create its source file; the fixture was corrected.
- Run `46138976012` exposed an existing inventory assertion that expected a database error type for a corrupt backup. Since the hardened verifier now returns `False` rather than raising, the inventory layer now converts that false result into a sanitized integrity-failure status.
- All failures remain in Actions history. The final exact SHA above passes the complete test suite and the dedicated Phase 14 workflow.

**Disposition:** U20-8-06 PASS. Next required unit: U20-8-07 — interrupted restore and rollback test on disposable fixtures. PR #71 remains draft and unmerged; `main` and live database state are untouched.
