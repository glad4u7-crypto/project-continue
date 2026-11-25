# Database Operations — Backup and Recovery

## Storage configuration

Set `PROJECT_CONTINUE_DB` to the SQLite database path. Development defaults to `.data/project_continue.sqlite3`. Production mode requires an absolute path on persistent storage.

## Create and verify a backup

Use the database backup API from a controlled maintenance process:

```python
from config import get_settings
from database import Database

database = Database(get_settings().database_path)
backup_path = database.backup("/var/backups/project-continue/project-continue.db")
assert Database.verify_backup(backup_path)
```

The backup API:
- Refuses to overwrite an existing destination.
- Creates parent directories when needed.
- Creates a new backup with owner-only permissions on POSIX systems.
- Uses SQLite's online backup API rather than copying an open database file.
- Runs SQLite integrity verification before returning.
- Provides a read-only integrity and foreign-key verification method.

Keep backups outside the repository and outside the live database directory. Protect them with the same access controls as the source database. Do not upload database backups to public repositories or include them in CI artifacts.

## Recovery procedure

1. Stop the Streamlit application so no process is writing to the database.
2. Verify the selected backup with `Database.verify_backup(path)`.
3. Preserve the current database as a separate recovery copy before replacement.
4. Restore the verified backup to the configured `PROJECT_CONTINUE_DB` path using the operating system's file-copy tools.
5. Confirm file ownership and permissions, then restart the application.
6. Verify project/task counts and recent activity before resuming normal use.

## Operational limitations

- Backups are manual/API-driven; no scheduler or retention policy is configured by this phase.
- Off-site replication and encryption-at-rest must be provided by the deployment/storage platform.
- A successful SQLite integrity check does not prove that a backup is recent or that every business-level record is correct.
- This repository does not currently implement a one-click restore UI.


## Runtime backend selection (Part 1)

SQLite remains the default and is selected when `PROJECT_CONTINUE_DB_BACKEND` is unset.

For an isolated PostgreSQL environment, explicitly set:

```bash
PROJECT_CONTINUE_DB_BACKEND=postgresql
PROJECT_CONTINUE_POSTGRES_DSN='postgresql://USER:PASSWORD@HOST:5432/DATABASE'
```

Keep the DSN in the host secret manager or an untracked environment file. Never commit it.
The runtime selector only chooses a backend; it does not migrate data, copy SQLite records,
create backups, or change a running deployment. Run PostgreSQL integration and migration
acceptance against a disposable database before any production decision. The current live
application remains on SQLite until all application services and acceptance gates pass.
