# Project Continue — Backup, Restore & Disaster Recovery Guide

## 1. Purpose and boundaries

This guide describes the existing SQLite backup primitives and the additional controls required on a selected production host. A verified local SQLite backup is necessary but not sufficient: production recovery also depends on private storage, encryption, off-site copies, monitoring and a tested restore procedure.

Never use the user's live Colab database as a restore target. Never stop/restart the current dashboard or reboot the runtime to perform this guide.

## 2. Required environment

On an always-on approved host, configure:
- `PROJECT_CONTINUE_DB`: absolute path to the active SQLite database.
- `PROJECT_CONTINUE_BACKUP_DIR`: separate private backup directory.

The runner uses `config.get_settings()`, `Database` and `BackupOperations.create_backup()`. It prints a safe JSON status and backup filename, not database content or exception details.

## 3. Create a verified backup

From the repository root in the application's supported Python environment:

```bash
python scripts/run_verified_backup.py
```

Expected success shape:
```json
{"status":"success","backup_name":"project-continue-<UTC timestamp>.sqlite3"}
```

A missing backup directory configuration exits with code 2. A backup/verification error exits non-zero and prints only a safe error type.

The implementation uses SQLite's online backup API and verifies the resulting database. Backups must be stored outside the live database directory. The selected host/operator must additionally configure storage encryption, private access controls, off-site replication and monitoring; these are not supplied automatically by the repository helper.

## 4. Scheduling and retention

Run the backup command from an external scheduler on an always-on host (for example, the host's system scheduler or managed job service). Choose cadence and retention based on the business RPO/RTO; do not assume any schedule has been configured by installing the application.

Suggested initial policy for operator review only:
- Daily verified backup.
- Weekly independent/off-site copy.
- Keep daily copies for 30 days and monthly copies for a longer approved period.
- Alert on any missed/failed backup.
- Perform a documented restore drill at least quarterly and before material upgrades.

This is a suggested policy, not a configured schedule or a claim that off-site copies exist.

Retention is preview-first:
1. Use `BackupOperations.preview_retention(keep_days=30)`.
2. Review the full candidate list and ensure it contains only managed backup files.
3. Apply deletion only with explicit operator authorization using `apply_retention(preview, confirm=True)`.
4. Record the result.

Never run retention against the active database directory. Never automatically delete files outside the managed backup namespace.

## 5. Isolated restore drill

A restore drill must use a new, non-existing path separate from the active database. The helper accepts only managed backup files within the configured backup root and rejects:
- symbolic-link backup sources;
- a destination equal to the live database;
- an existing destination;
- a destination equal to the source;
- a backup failing integrity verification.

Example (adapt paths and run only on an approved isolated host/test copy):
```python
from database import Database
from services.backup_operations import BackupOperations

db = Database("/var/lib/project-continue/project_continue.sqlite3")
ops = BackupOperations(db, "/var/backups/project-continue")
restored = ops.restore_drill(
    "/var/backups/project-continue/project-continue-<verified-file>.sqlite3",
    "/var/tmp/project-continue-restore-drill.sqlite3",
)
print("Restored isolated copy:", restored.name)
db.close()
```

After the SQLite integrity check, open the restored copy in an isolated application/test environment. Verify expected project/task counts and run the full test suite against the restored copy where supported. A successful SQLite integrity check alone does not prove all application-level records and workflows are correct.

Do not copy a live production DB into this chat or GitHub.

## 6. Actual disaster recovery / cutover

An actual recovery is a separately approved operator action:
1. Declare incident and record affected release/host.
2. Preserve the current database and logs; do not overwrite.
3. Identify the latest verified backup and confirm its timestamp/integrity.
4. Confirm the chosen restore point meets the incident's RPO.
5. Schedule a maintenance window and stop all writers using the provider's approved procedure.
6. Restore to a new path.
7. Validate schema, key record counts, application startup and authorization.
8. Change the host's database configuration only after validation.
9. Reopen access, monitor and record the outcome.
10. Retain the pre-recovery database for investigation according to policy.

This sequence is documentation only; no live recovery or cutover has been performed.

## 7. RPO/RTO and ownership

The product repository does not define a business RPO/RTO. The service owner must approve them based on acceptable data loss and recovery time, then set the backup cadence and storage design accordingly.

Record:
- backup owner and on-call contact;
- backup cadence and latest successful timestamp;
- retention and encryption settings;
- off-site destination and access policy;
- last successful restore drill;
- approved RPO/RTO;
- incident escalation and rollback decision owner.

## 8. Acceptance checklist

- [ ] Backup directory is separate, private and durable.
- [ ] Host encryption/access controls are verified.
- [ ] Scheduler runs on an always-on host.
- [ ] Success/failure alerts are tested.
- [ ] Retention preview is reviewed before deletion.
- [ ] Off-site copy is verified.
- [ ] Restore drill succeeds to a new isolated path.
- [ ] Application-level records and tests pass on restored copy.
- [ ] RPO/RTO and operational owner are documented.
- [ ] No operation touched the live Colab runtime/database.
