# Phase 14 — Production Operations Runbook

## Deployment profile

The application currently supports Streamlit + SQLite. A production deployment requires:
- A host with a persistent private volume and filesystem access controls.
- HTTPS termination and a supported identity/session integration.
- Host-managed secret storage for `SESSION_SIGNING_KEY` (at least 32 random bytes) and integration credentials.
- A single-writer or explicitly coordinated SQLite deployment model; do not put SQLite on an arbitrary network filesystem.
- An external scheduler on an always-on host. A disconnected Colab runtime is not a scheduler.
- A private backup destination with a separately defined retention and encryption policy.

Do not publicly expose the app until login and server-side authorization have been integrated into every data-bearing page and service call.

## Identity and authorization primitives

`services/access_control.py` provides scrypt password hashes, HMAC-signed expiring sessions, project membership roles (owner/editor/viewer), admin role, access-denial exceptions and audit events. It is a server-side primitive, not a substitute for wiring a login gate and calling `require_project` at every service boundary. Production mode currently allows only admin-role operators through the global gate. The current Streamlit pages are not yet a complete authenticated multi-user application; project membership checks must be wired into every page/service before enabling multi-user access.

Provision the initial owner using a controlled operator process. `bootstrap_project_owner` is one-time per project and refuses to replace an existing owner. Never create a default password or commit session signing keys.

## Backups

Use `BackupOperations(database, backup_root)` from an external scheduled process. `create_backup()` uses the SQLite online backup API and verifies integrity. Store backups outside the repository and live database directory; restrict access and encrypt storage using the selected host's facilities.

Run `python scripts/run_verified_backup.py` from the repository root on an always-on host after setting `PROJECT_CONTINUE_DB` and `PROJECT_CONTINUE_BACKUP_DIR`. The script emits only a safe status and backup filename; schedule it with the host's cron/system scheduler, not a GitHub-hosted runner that cannot see the private SQLite file.\n\nRetention is preview-first:
1. Call `preview_retention(keep_days=...)`.
2. Review every returned candidate.
3. Only an authorized operator may call `apply_retention(preview, confirm=True)`.

Restore drills must target a new isolated path. `restore_drill` rejects the live database path, existing destinations and unmanaged backup files. A successful SQLite integrity check is not proof of application-level correctness; compare expected record counts and run application tests against the restored copy.

## Recovery and cutover

Never restore over the active database as an automated operation. For an actual production cutover, use a separately approved maintenance window, stop writers, preserve the current DB, verify the chosen backup, restore to a new path, validate business records, then change the host's DB configuration and restart under operator control. This procedure is intentionally not executed against the user's Colab runtime.

## Health and logs

`operational_health` reports only ready/not-ready and a database status label. It does not return database paths, SQL details, credentials or user records. Production logs must follow the same rule.

## Acceptance boundaries

CI and isolated tests do not establish that a public host is secure. Final release acceptance separately requires: all automated checks; manual browser authentication/authorization checks; provider-specific HTTPS, persistent storage, secret-store and backup evidence; a restore drill on the target host; and an operator-approved deployment.
