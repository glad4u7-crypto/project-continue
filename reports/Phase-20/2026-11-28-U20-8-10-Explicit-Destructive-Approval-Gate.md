# U20-8-10 — Explicit approval gate for destructive recovery actions

**Date:** 2026-11-28 (Asia/Kolkata)  
**Repository:** glad4u7-crypto/project-continue  
**Branch:** phase20/secure-dispatcher-u20-3-01  
**Exact tested SHA:** `92fa07fc6eacc4891d69c9f2a02a5836d126ffa5`  
**Disposition:** **PASS — destructive backup deletion is explicitly gated; restore/overwrite remain fail-closed**

## Implemented gate

Updated `services/backup_operations.py`:

- A retention preview remains read-only. Deletion requires a `DestructiveApproval` issued for one exact candidate in that exact preview.
- Issuance requires a non-empty approver label and the exact target-specific phrase `APPROVE DELETE <filename>`.
- The approval carries an opaque random token, action, canonical target, preview SHA-256, approver and issue timestamp.
- The token is held in the issuing `BackupOperations` instance and is single-use. Wrong target, changed preview, wrong action/scope, missing approval and replay are rejected.
- Legacy `confirm=True` is explicitly rejected; a boolean is not authorization.
- Every candidate and approval in a batch is preflighted before the first unlink, preventing partial deletion when any item lacks valid approval.
- Approval issue/consume events are exposed as sanitized in-process audit records. A host integration must persist these records to its approved durable audit sink; this repository helper does not claim durable audit storage.
- Existing restore protections remain fail-closed: restore cannot target the live database, existing destinations are not overwritten, and idempotent restore only accepts a verified identical destination as a no-op. No live restore or overwrite pathway was introduced.

## Tests

Updated `tests/test_backup_operations.py` with coverage for:
- missing approval and boolean-only confirmation rejection;
- exact phrase and named approver requirement;
- approval bound to exact preview and target;
- replay rejection;
- preflight of all batch approvals before any deletion;
- approval audit issue/consume events;
- retention deletion only on disposable pytest `tmp_path` fixtures.

The first implementation attempt at code SHA `4c9b8de0488001c2ca1224c79d069e9c71358daf` exposed three test failures: replay after file removal was silently skipped, the untrusted-path test observed the legacy boolean rejection first, and multi-candidate retention could partially delete before discovering a missing approval. These failures were preserved and corrected in the follow-up commit; the final implementation preflights every candidate and approval before mutation.

## Exact-SHA CI evidence

On exact code SHA `92fa07fc6eacc4891d69c9f2a02a5836d126ffa5`:

- Main Project Continue CI [run 46141183933](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141183933) — **SUCCESS**. Secret scan, dependency audit, compile, production container build, Compose validation, smoke test, focused categories and full regression passed. Full suite: **464 passed, 11 skipped, 52 subtests passed**; coverage **80%**. Test/coverage artifact ID `15261198696` (345,290 bytes); Gitleaks SARIF artifact `15260879268` (6,796 bytes).
- Fixed-task runner [run 46141183921](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141183921) — SUCCESS; compile, dispatcher tests (69 passed, 47 subtests) and full regression passed.
- PostgreSQL integration [run 46141183914](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141183914) — SUCCESS; **475 passed, 52 subtests passed** against PostgreSQL 16.
- Notebook sandbox [run 46141184150](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141184150) — SUCCESS; harmless two-cell E2E, non-root kernel, network denial, timeout and kernel-crash failure modes passed; artifact ID `15262035281`.
- Dashboard browser [run 46141183925](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141183925) — SUCCESS; CRUD/reload and browser acceptance passed; artifact ID `15261807632`.
- Cloud Acceptance [run 46141183940](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141183940) — SUCCESS on Python 3.11 and 3.13.
- Phase 13 [run 46141183897](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141183897) — SUCCESS.
- Phase 14 [run 46141183965](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141183965) — SUCCESS on Python 3.11 and 3.13.

## Separate unresolved dashboard-health signal

The separate dashboard-health run [46141179398](https://github.com/glad4u7-crypto/project-continue/actions/runs/46141179398) failed on this SHA but GitHub returns `jobs=[]`; the earlier run [46140424680](https://github.com/glad4u7-crypto/project-continue/actions/runs/46140424680) has the same no-job condition. GitHub rejected retry of the earlier run with HTTP 403 (“This workflow run cannot be retried”). With no job or step logs, the root cause cannot be established from the available GitHub connector. This is retained as an unresolved operational diagnostic, not counted as a successful health check and not treated as evidence against the backup-approval unit.

## Safety and boundaries

- All deletion tests used disposable pytest temporary directories only.
- No actual backup was deleted; no restore or overwrite was performed.
- No production DB, Drive mount/content, deployment or live Streamlit service was touched.
- PR #71 remains open, draft and unmerged; main branch unchanged.

**Final status: U20-8-10 PASS.** Phase 20.8 has 9/10 PASS and U20-8-09 remains UNAVAILABLE because live Google Drive access is disabled by the account administrator.