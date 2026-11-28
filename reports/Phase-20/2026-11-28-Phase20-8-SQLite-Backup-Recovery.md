# Phase 20.8 — SQLite Backup and Recovery Safety

- Date: 2026-11-28 (Asia/Kolkata)
- Repository: `glad4u7-crypto/project-continue`
- Branch: `phase20/u20-8-sqlite-backup-recovery`
- Final tested commit: `068b7d5230f4a1dd0102ee9363460effc3ff6fd6`
- Dedicated fixed-task runner: [46118338614](https://github.com/glad4u7-crypto/project-continue/actions/runs/46118338614) — SUCCESS
- Main CI: [46118338594](https://github.com/glad4u7-crypto/project-continue/actions/runs/46118338594) — pending final confirmation at report creation
- Dedicated SQLite safety acceptance: 33 passed
- Full regression: 435 passed, 11 skipped (PostgreSQL DSN-dependent), 52 subtests passed
- No merge; no main-branch mutation; no live database or Drive mount was touched.

## Implemented controls

1. Pytest file-backed SQLite guard permits temporary roots and blocks configured/default live database paths.
2. Backup storage must be separate from the live database directory tree; backup/source/destination symlink path components are rejected.
3. SQLite inspection runs integrity and foreign-key checks and validates the application schema version.
4. Backup creation writes a restricted manifest with archive identity, size, SHA-256, schema and integrity metadata; verification re-computes these values.
5. Inventory distinguishes verified and invalid backups. Restore preview is read-only.
6. Corrupt/truncated backups and schema mismatches are rejected.
7. Restore drills use exclusive destination creation, never overwrite an existing destination or the live DB, and remove partial output on interruption.
8. Replaying restore against an existing destination is rejected; existing restored rows remain unchanged.
9. Drive-like sentinel content is preserved; no Drive mount or Drive path mutation is performed.
10. Retention is preview-first and requires explicit confirmation plus approval ID; stale/modified archive or manifest data is rejected. Destructive authorization binds approval to exact target SHA-256 and performs no mutation itself.

## Acceptance evidence

- Runner log: SQLite acceptance `33 passed in 0.30s`; full regression `435 passed, 11 skipped, 52 subtests passed`.
- Earlier failed runs were retained as evidence and corrected:
  - Retention fixture namespace assumptions were updated to the preview-ID/approval-ID contract.
  - Backup root validation was refined to allow a dedicated backup subdirectory while rejecting a backup root that contains the live DB.
  - Pytest safety guard was widened to allow isolated `TemporaryDirectory` databases while blocking the configured live path.
  - Dashboard AppTest fixtures now inject isolated settings rather than relying on environment mutation after import.
- Final dedicated runner success is on the exact tested SHA above. Main CI status is recorded separately and must be successful before PR readiness is asserted.
- Optional Ruff lint remains SKIPPED because Ruff is not installed; no dependency was added.
- PostgreSQL integration/backup/migration tests remain skipped because their dedicated DSNs are not configured. This is not represented as a pass.

## Unit checkpoint dispositions

| Unit | Result | Evidence |
|---|---|---|
| U20-8-01 | PASS | pytest SQLite guard; temp path and TemporaryDirectory tests |
| U20-8-02 | PASS | configured/default live DB blocked in test guard |
| U20-8-03 | PASS | integrity_check, foreign_key_check, schema-version checks |
| U20-8-04 | PASS | backup manifest and SHA-256 recomputation tests |
| U20-8-05 | PASS | verified inventory and read-only restore preview |
| U20-8-06 | PASS | corrupt/truncated and mismatched-schema rejection tests |
| U20-8-07 | PASS | interrupted restore cleanup test |
| U20-8-08 | PASS | restore replay rejection preserves existing restored row |
| U20-8-09 | PASS | Drive-like sentinel remains unchanged; no mount |
| U20-8-10 | PASS | explicit approval ID, exact SHA binding, no-mutation authorization |

## Scope and limitations

This phase supplies local SQLite backup/restore safety primitives and tests; it does not perform a real restore/delete/overwrite of production data. Human approval gates are validation-only. PostgreSQL-specific backup/recovery remains unverified without DSNs. The unrelated dashboard-health workflow reports failure on this branch; it is not the Phase 20.8 dedicated acceptance workflow or main CI acceptance gate, and is retained for separate diagnosis.
