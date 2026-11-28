# U20-8-09 — Google Drive backup preservation verification

**Date:** 2026-11-28 (Asia/Kolkata)  
**Repository:** glad4u7-crypto/project-continue  
**Branch:** phase20/secure-dispatcher-u20-3-01  
**Exact tested SHA:** `80f74422a460a775b2a39ca9b4ea947891e1c29c`  
**Disposition:** **UNAVAILABLE — live Drive source could not be inspected**

## Read-only repository/notebook audit

Reviewed `notebooks/ProjectContinue-Recovery.ipynb` and `docs/COLAB-PERMANENT-RECOVERY.md`.

The checked-in recovery notebook's source-preservation contract is:

- Mounts `/content/drive` normally; it does not request `force_remount` or unmount Drive.
- Selects a manifest-bearing `recovery_full_*` directory under `MyDrive/Project-Continue-Backups`.
- Copies the selected tree into a distinct timestamped directory under `MyDrive/Project-Continue-Recovery-Restores`.
- Refuses to copy if that destination already exists.
- Compares source and restored relative file inventories and checks that the source still exists.
- No source deletion, move, rename, unlink or overwrite call exists in the notebook code cells.

Added `test_recovery_notebook_copy_contract_preserves_source_backup` to `tests/test_notebook_validation.py`. The test statically checks the mount/copy/no-overwrite contract and parses notebook code cells with Python AST to reject destructive file-operation calls. This is a repository regression guard; it does not simulate or inspect the user's real Drive files.

## Exact-SHA CI evidence

Main Project Continue CI [run 46140425829](https://github.com/glad4u7-crypto/project-continue/actions/runs/46140425829) checked out `80f74422a460a775b2a39ca9b4ea947891e1c29c` and completed **SUCCESS**:

- Secret scan, dependency audit, Python compile, production container build, Compose validation, production-container smoke test, focused test categories and complete regression suite all passed.
- Full suite: **462 passed, 11 skipped, 52 subtests passed**.
- Coverage: **80%**.
- Test/coverage artifact ID `15261197682`, 339,785 bytes, SHA-256 `fc8aabfbf20500b476bebf5b17789f7f6525da654845d1df1ef733edaa349917`.
- Gitleaks SARIF artifact ID `15261845844`, 6,796 bytes, SHA-256 `0b25631a6a97a3a522bc5a5358c03eb645256254e95d35874d2fef04e8d73e9f`.

The separate dashboard-health workflow [run 46140424680](https://github.com/glad4u7-crypto/project-continue/actions/runs/46140424680) failed on the same SHA. It is an operational health check, not evidence about Drive backup preservation; it remains recorded separately and is not counted as a passing test.

## Why live Drive verification is unavailable

The live Google Drive connector was discovered in the plugin directory but is marked **DISABLED_BY_ADMIN / NOT_AVAILABLE**. There is no connected Drive read capability in this session. No exact Drive folder URL/file ID or live Drive file metadata was available to inspect.

Consequently, this work cannot establish that an actual `recovery_full_*` backup currently exists, that its manifest is readable, that its files/hashes match, or that the real source folder remains unchanged. Static notebook inspection and CI do not prove those live facts.

## Safety

No Drive mount was created, changed, force-remounted or unmounted. No Drive file was read, copied, deleted, moved, renamed or overwritten. No Colab runtime, production database, deployment or live service was touched. PR #71 remains draft and unmerged; `main` is unchanged.

**Final status: U20-8-09 UNAVAILABLE (not PASS).** To close the live verification gap, Google Drive access must first be made available by the account administrator; then the exact backup folder link/file ID can be supplied for a read-only manifest, file inventory and hash/preservation check.

**Next unit:** U20-8-10 — separate explicit approval gate for any real restore/delete/overwrite.
