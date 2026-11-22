# S027-004 — Zero-Cost Production Operational Handover

**Decision:** Strict operating budget = INR 0/month. Paid VPS, paid object storage, paid monitoring, and services requiring a payment method are excluded.

**Branch:** `docs/s027-004-zero-cost-handover`  
**Baseline:** `f37dbd7569324823e707c6d7e344128d836bddcd`  
**Scope:** Documentation-only decision record. No production configuration, database, Colab runtime, Streamlit process, secrets, or workflow schedules were changed.

## 1. Executive decision

A fully automated, always-on production backup and recovery service cannot honestly be accepted under the currently verified zero-cost constraints.

The existing backup runner is designed for an always-on host. It requires an absolute production DB path and `PROJECT_CONTINUE_BACKUP_DIR`; it exits with code 2 when the backup directory is missing. The repository runbook explicitly says Colab disconnects are not reliable scheduling and a GitHub-hosted runner cannot see the private SQLite file in the user's Colab runtime.

The repository is public. Therefore the production SQLite database, backup archives, encryption keys, credentials, or user data MUST NOT be committed, uploaded as public workflow artifacts, or stored in public releases.

Scheduled GitHub Actions that execute repository tests are CI, not production DB backups. They must not be relabeled as a production backup scheduler.

## 2. Verified current state carried forward

- Production DB preservation and prior integrity/hash checks: PASS per S027-003B user-supplied evidence.
- Dashboard health: PASS per S027-003B user-supplied evidence; PID 7388 / port 8501 was reported active.
- Backup/restore implementation: present in `services/backup_operations.py`.
- Isolated backup/restore drill: 20/20 PASS per S027-003B user-supplied evidence.
- Backup entry point: `scripts/run_verified_backup.py`.
- Production backup directory: not provisioned.
- Always-on production scheduler: not provisioned.
- Encrypted off-site copy: not established.
- Production alerting: not established.
- Applied retention policy: not established.
- Approved RPO/RTO and production recovery handover: not established.

### Zero-cost storage discovery (2026-11-22)

- A Dropbox connector is available and its root folder listing was readable.
- The root listing showed no dedicated Project Continue backup destination.
- The available Dropbox tools did not expose account quota/free-space figures, so sufficient free capacity is **UNVERIFIED**.
- A connected Dropbox account is a possible private destination for encrypted archives, but it does not provide a scheduler or give GitHub Actions/Colab an always-on path to the production DB.
- No folder was created, no file was uploaded, and no Dropbox account identity or unrelated folder names are recorded here.
- Creating a dedicated folder and uploading a test ciphertext require a separate explicit destination/mutation approval.

No claim is made that the live application/database state was rechecked by this documentation-only change.

## 3. Zero-cost feasibility matrix

| Control | Zero-cost feasibility | Honest status |
|---|---|---|
| Backup code and isolated tests | Yes; already in repository | IMPLEMENTED / TESTED |
| GitHub scheduled CI | Yes, subject to plan quotas | CI ONLY; cannot read Colab DB |
| Colab-local backup while runtime is active | Technically possible | MANUAL / SESSION-BOUND |
| Reliable always-on scheduler on free Colab | No guarantee | NOT ACCEPTED |
| Private off-site storage | Dropbox connector exists, but quota and dedicated destination are unverified | NOT PROVISIONED |
| Client-side encryption | Possible with local tooling and protected key custody | NOT DEPLOYED |
| Automatic retention | Requires a dependable runner and storage target | NOT DEPLOYED |
| Failure alerting | Possible only after a reliable monitor and notification destination are configured | NOT DEPLOYED |
| Production RPO/RTO | Cannot be promised without measured backup cadence and restore time | UNDEFINED |

Free-tier limits, quotas, account eligibility, inactivity rules, and provider terms can change. No third-party free tier is treated as an availability or durability SLA.

## 4. Prohibited unsafe shortcuts

1. Do not put the live SQLite database or backups in this public GitHub repository, Releases, or Actions artifacts.
2. Do not place encryption keys, tokens, passwords, signing keys, or personal data in GitHub source, workflow YAML, logs, or chat.
3. Do not make a scheduled GitHub workflow that assumes it can access the Colab filesystem.
4. Do not claim Colab is an always-on host or use a background loop as a reliable scheduler.
5. Do not run retention deletion against the live database directory.
6. Do not restore over the active database.
7. Do not reboot the Colab runtime or stop/restart the running Streamlit dashboard.
8. Do not change `PROJECT_CONTINUE_DB`, `APP_ENV`, `SESSION_SIGNING_KEY`, or the live backup configuration as part of this zero-cost decision.

## 5. Safe zero-cost interim procedure

Until an approved private storage destination and reliable scheduler exist, the only safe interim posture is **manual, operator-triggered backup while the existing runtime is already available**:

1. Use the existing verified backup implementation against the intended database only after confirming the exact DB path in the active runtime.
2. Set a separate backup directory outside the repository and outside the live DB directory.
3. Create the backup using SQLite's online backup API and verify integrity.
4. Encrypt the backup client-side before transferring it to any cloud destination. Keep the encryption key separate from the archive and never upload the key beside the archive.
5. Transfer only to a private destination that the account owner has explicitly authorized and whose free quota/access controls have been checked.
6. Verify the uploaded ciphertext by checksum and retain the local verified copy until the off-site copy is confirmed.
7. Do not automate deletion/retention until the destination, key recovery, and restore procedure have been tested.

This procedure is a safe interim runbook, not proof that a recurring backup has been scheduled. It requires operator action and does not protect against a Colab disconnect before the operator runs it.

## 6. RPO/RTO decision

- **Production RPO:** UNDEFINED / NOT COMMITTED.
- **Production RTO:** UNDEFINED / NOT COMMITTED.

A 24-hour RPO or RTO must not be promised while no reliable daily scheduler, durable private destination, and measured restore drill exist. The service owner must approve business targets after a real backup and restore cadence has been measured.

## 7. Acceptance gates

S027-004 remains **BLOCKED — ZERO-COST HOSTING / SCHEDULER CAPABILITY NOT ESTABLISHED** until all of the following are evidenced:

- [ ] A private, durable, zero-cost storage destination is authorized and has sufficient available quota.
- [ ] Client-side encryption and independent key recovery are demonstrated.
- [ ] A reliable scheduler that can access the production DB is available without depending on a disconnected Colab session.
- [ ] A verified backup is created on schedule and its timestamp/size/checksum are recorded.
- [ ] A failure/missed-run alert is delivered and tested.
- [ ] Retention is previewed, approved, and safely applied only to managed backup copies.
- [ ] An off-site encrypted backup is downloaded and restored to a new isolated path.
- [ ] Application-level record checks and tests pass on the isolated restored copy.
- [ ] RPO/RTO are approved and measured.
- [ ] Operator handover records the owner, recovery-key custody, destination, cadence, retention, alert route, and last restore evidence.

## 8. Current safety boundary

This branch contains documentation only. It does not alter `main`, deploy a host, configure a scheduler, create a Dropbox folder, provision storage, copy the production DB, or touch the running Colab/Streamlit environment.

**Final decision:** Do not mark S027-004 Production Operational Handover ACCEPTED under the current strict INR 0/month constraint. Preserve the verified application and database state; proceed only when the zero-cost access/scheduler/storage prerequisites can be demonstrated.
