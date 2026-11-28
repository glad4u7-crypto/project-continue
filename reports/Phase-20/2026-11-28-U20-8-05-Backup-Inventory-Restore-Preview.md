# U20-8-05 — Backup inventory and restore preview-only report

**Timestamp:** 2026-11-28 16:19 Asia/Kolkata  
**Repository:** glad4u7-crypto/project-continue  
**Branch:** phase20/secure-dispatcher-u20-3-01  
**Exact code SHA:** `89dcd8eba3f7f6c3636330f30e3aba724319c94d`  
**Result:** PASS

## Implementation

Extended `database/backup.py` with two strictly read-only operations:

- `inventory_backups(directory)` scans only the immediate directory, accepts regular `.db`, `.sqlite`, and `.sqlite3` files, skips symlinks/non-regular files, and caps the inventory at 500 files. It records filename, size, UTC modification time, SHA-256 and a read-only SQLite schema/integrity inspection result. Invalid database files remain visible with a sanitized `sqlite_inspection_failed` status.
- `preview_backup_restore(path, expected_sha256)` checks the supplied digest, supported schema version, `integrity_check`, and `foreign_key_check`. It has no destination parameter and returns `restore_performed=False` for every result. A candidate is merely eligible for a separate manual review; this is not restore approval.
- Symlinked backup directories and symlinked restore candidates are rejected.
- The API and typed result records are exported from `database`.
- `docs/DATABASE-OPERATIONS.md` documents the preview-only workflow and its non-authorizing nature.

No restore, copy, deletion, overwrite, live database access, or production backup was performed.

## Tests added

- Inventory lists only regular backup database files, excludes symlink aliases and unrelated extensions, and reports checksum/integrity.
- Invalid SQLite files remain visible with a sanitized inspection error; source bytes remain unchanged.
- Missing inventory directories are not created; symlinked directories are rejected.
- A valid checksum/schema/integrity candidate is previewed as eligible for manual review only.
- Checksum mismatch, corrupt SQLite, unsupported schema, missing file, and symlink candidates are rejected.
- Preview leaves the backup SHA unchanged and creates no destination file or directory.

All test databases and backup files are under pytest `tmp_path`.

## Exact-SHA CI evidence

All listed runs checked out exact code SHA `89dcd8eba3f7f6c3636330f30e3aba724319c94d`:

- Main Project Continue CI: [run 46138611341](https://github.com/glad4u7-crypto/project-continue/actions/runs/46138611341) — SUCCESS.
  - Secret scan, dependency audit, compile, production Docker build, Compose validation, container smoke test, focused test categories and full regression passed.
  - Full suite: **455 passed, 11 skipped, 52 subtests passed**.
  - Coverage: **80%**.
  - Test/coverage artifact ID: `15260309795`, SHA-256 digest `b1d09e6fceadef54ffe98407ae071e77be2d4420534866e5e0e96e157d08f7e7`.
- Fixed-task runner: [run 46138614954](https://github.com/glad4u7-crypto/project-continue/actions/runs/46138614954) — SUCCESS.
- PostgreSQL integration: [run 46138614982](https://github.com/glad4u7-crypto/project-continue/actions/runs/46138614982) — SUCCESS.
- Notebook sandbox: [run 46138614858](https://github.com/glad4u7-crypto/project-continue/actions/runs/46138614858) — SUCCESS.
- Phase 13: [run 46138614883](https://github.com/glad4u7-crypto/project-continue/actions/runs/46138614883) — SUCCESS.
- Phase 14: [run 46138614963](https://github.com/glad4u7-crypto/project-continue/actions/runs/46138614963) — SUCCESS.

Dashboard Browser Acceptance `46138614914` and Cloud Acceptance `46138614952` were cancelled by workflow concurrency; they are not counted as PASS evidence for this unit. The required main CI, runner, database and notebook checks above passed.

## Preserved failure history

- Run `46138403534` found that the inventory fixture placed its source database inside the directory being inventoried, so two valid database files were correctly returned. The fixture was corrected to keep the source database outside the inventory root.
- Run `46138508739` exposed an existing test fixture that expected an unmanaged-source error but had not created the source file; strict path resolution correctly raised `FileNotFoundError`. The fixture now creates an existing unmanaged file before asserting rejection.
- These failures are preserved in Actions history. The corrected exact SHA above passes the complete suite.

**Disposition:** U20-8-05 PASS. Next required unit: U20-8-06 — reject corrupt/truncated backup tests. PR #71 remains draft and unmerged; `main` and live database state are untouched.
