# U20-8-10 — Explicit approval gate for destructive recovery actions

**Date:** 2026-11-28 (Asia/Kolkata)  
**Repository:** glad4u7-crypto/project-continue  
**Branch:** phase20/secure-dispatcher-u20-3-01  
**Exact tested code SHA:** `6faa307ee82f88b9feeb6fb1fc08eca73022f03b`  
**Disposition:** **PASS — restore and delete require scoped one-time approvals; overwrite/live restore remain fail-closed**

## Implemented approval controls

Updated `services/backup_operations.py`:

- Retention deletion requires a `DestructiveApproval` issued for one exact candidate in the exact retention preview.
- Restore to a new destination also requires a separate approval, bound to the verified source backup filename + SHA-256 and the exact resolved destination.
- Approval issuance requires a non-empty approver label and an exact action-specific phrase:
  - `APPROVE DELETE <filename>`
  - `APPROVE RESTORE <destination-filename> FROM <backup-filename>`
- Each approval carries an opaque random token, action, canonical target, SHA-256 scope digest, approver and issue timestamp.
- Tokens are registered in the issuing `BackupOperations` instance and are single-use. Missing approval, wrong action, wrong target, changed preview/source, and replay are rejected.
- Legacy boolean `confirm=True` is explicitly rejected; a boolean is not authorization.
- Retention batch operations preflight every candidate and every approval before the first unlink, preventing partial deletion if any candidate lacks valid approval.
- Idempotent restore of an already existing byte-identical verified destination remains a no-op; creating a new destination requires approval.
- Live database restore remains prohibited; existing destinations are never overwritten. No overwrite operation is exposed, so overwrite attempts remain fail-closed.
- Approval issue/consume events are available as sanitized in-process audit records. A host integration must persist these records to its approved durable audit sink; this helper does not claim durable audit storage.

## Test coverage

Updated `tests/test_backup_operations.py` to verify:
- deletion rejected without approval or with boolean-only confirmation;
- exact delete phrase and named approver required;
- delete approval is bound to one candidate and exact preview;
- replay and altered-preview attempts rejected;
- all approvals preflight before any batch deletion;
- restore rejected without approval;
- restore approval binds source checksum and exact destination;
- wrong confirmation and replay/wrong-destination attempts rejected;
- restore fault-injection/rollback and idempotent replay remain protected;
- all destructive-path tests use disposable pytest `tmp_path` fixtures only.

### Preserved failed attempts and corrections

- SHA `4c9b8de0488001c2ca1224c79d069e9c71358daf`: three approval/deletion tests failed; corrected by preflighting the entire batch, validating namespace before the legacy boolean gate, and rejecting replay even after the file disappears.
- SHA `15928a1c7a3a5067e411a35422b3186d50983858`: two fault-injection tests exposed verification-call sequencing after restore approval preflight; adjusted test injection to the new call sequence.
- SHA `eb4786cb4ef87967b746c4365a9c32922f659592`: one assertion still expected the old call count; corrected in the next commit.
- These failed runs remain in GitHub Actions history; they were not erased or reclassified as passing.

## Exact-SHA CI evidence

All runs below checked out exact code SHA `6faa307ee82f88b9feeb6fb1fc08eca73022f03b`:

- Main Project Continue CI [run 46141650305](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141650305) — **SUCCESS**. Secret scan, dependency audit, Python compile, production container build, Compose validation, smoke test, focused categories and full regression all passed. Full suite: **465 passed, 11 skipped, 52 subtests passed**; coverage **80%**. Test/coverage artifact ID `15261024777` (349,758 bytes); Gitleaks SARIF artifact ID `15262036031` (6,796 bytes).
- Fixed-task runner [run 46141650239](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141650239) — SUCCESS; compile, dispatcher suite (69 passed, 47 subtests) and full regression passed.
- PostgreSQL integration [run 46141650240](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141650240) — SUCCESS against PostgreSQL 16; **476 passed, 52 subtests passed**.
- Notebook sandbox [run 46141650244](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141650244) — SUCCESS; 24 tests, non-root kernel, network denial, harmless E2E, timeout and kernel-crash checks passed; artifact ID `15262395504`.
- Dashboard browser [run 46141650226](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141650226) — SUCCESS; browser CRUD/reload and read-only acceptance passed; artifact ID `15262010560`.
- Cloud Acceptance [run 46141650228](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141650228) — SUCCESS on Python 3.11 and 3.13; each full suite reported 465 passed, 11 skipped, 52 subtests.
- Phase 13 [run 46141650249](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141650249) — SUCCESS.
- Phase 14 [run 46141650232](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141650232) — SUCCESS on Python 3.11 and 3.13; focused security/operations tests and full regression passed.

## Separate unresolved dashboard-health signal

Dashboard-health [run 46141645718](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141645718) failed on the same SHA, but GitHub returns `jobs=[]`, so no job or step log exists to identify the root cause. Earlier run [46140424680](https://github.com/glad4u7-crypto/project-continue/actions/runs/46140424680) had the same no-job condition and GitHub rejected retry with HTTP 403 (“This workflow run cannot be retried”). This remains an unresolved operational diagnostic, not a passing health check and not evidence against the approval-gate tests.

## Safety and boundaries

- All restore/delete tests used disposable pytest temporary directories only.
- No actual backup was deleted; no live restore or overwrite was performed.
- No production DB, Drive mount/content, deployment or live Streamlit service was touched.
- PR #71 remains open, draft and unmerged; main branch unchanged.

**Final status: U20-8-10 PASS.** Phase 20.8 is 9/10 PASS; U20-8-09 remains UNAVAILABLE because live Google Drive access is disabled by the account administrator.