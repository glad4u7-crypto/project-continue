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


## Latest exact-head verification addendum

**Retest timestamp:** 2026-11-28 16:42 Asia/Kolkata  
**Latest exact code SHA:** `e5f60887d544940e4fcb74958499842f7c34209a`

The above implementation and its original evidence were revalidated on the current feature-branch head. The latest patch additionally provides `BackupOperations.inventory_backups()` and `BackupOperations.preview_restore()` for managed backup roots, including preflight rejection of symlink/unmanaged sources, the live database target, existing destinations and source/destination identity. A successful destination preview records `actions_performed=()` and does not create the destination or its parent.

All following workflows checked out the exact SHA above and succeeded:

- Main CI [run 46138628921](https://github.com/glad4u7-crypto/project-continue/actions/runs/46138628921): **455 passed, 11 skipped, 52 subtests passed**; compile, secret scan, dependency audit, container build, Compose validation, smoke test, focused tests and full regression passed. Artifact ID `15260911078`, 329,900 bytes, SHA-256 `2557c83c2e2e5b03ce037c179aca67b2bf439bebb8ea9b4fc7a8384da27b115c`.
- Fixed-task runner [run 46138628969](https://github.com/glad4u7-crypto/project-continue/actions/runs/46138628969): SUCCESS; **455 passed, 11 skipped, 52 subtests passed**.
- PostgreSQL integration [run 46138628917](https://github.com/glad4u7-crypto/project-continue/actions/runs/46138628917): SUCCESS; **466 passed, 52 subtests passed**.
- Notebook sandbox [run 46138628936](https://github.com/glad4u7-crypto/project-continue/actions/runs/46138628936): SUCCESS.
- Dashboard Browser Acceptance [run 46138629069](https://github.com/glad4u7-crypto/project-continue/actions/runs/46138629069): SUCCESS.
- Cloud Acceptance Lab [run 46138628981](https://github.com/glad4u7-crypto/project-continue/actions/runs/46138628981): SUCCESS on Python 3.11 and 3.13.
- Phase 13 [run 46138628988](https://github.com/glad4u7-crypto/project-continue/actions/runs/46138628988): SUCCESS.
- Phase 14 [run 46138628918](https://github.com/glad4u7-crypto/project-continue/actions/runs/46138628918): SUCCESS.

The 11 main-CI skips are opt-in PostgreSQL DSN tests; the isolated PostgreSQL integration run passed independently. The earlier failed run `46138492898` on SHA `835de52a3c38076e3a16148bddd7ea1575992663` remains preserved; its two failures were corrected and the current exact-head full suite passes.
