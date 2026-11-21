"""Scheduler entry point for verified local SQLite backups.

Run from an always-on production host via its scheduler. Colab disconnects are not
reliable scheduling. Required env: PROJECT_CONTINUE_DB, PROJECT_CONTINUE_BACKUP_DIR.
"""
import json
import os
import sys

from config import get_settings
from database import Database
from services.backup_operations import BackupOperations


def main() -> int:
    backup_dir = os.environ.get("PROJECT_CONTINUE_BACKUP_DIR", "").strip()
    if not backup_dir:
        print("Backup failed: PROJECT_CONTINUE_BACKUP_DIR is not configured.", file=sys.stderr)
        return 2
    settings = get_settings()
    database = Database(settings.database_path)
    try:
        path = BackupOperations(database, backup_dir).create_backup()
        print(json.dumps({"status": "success", "backup_name": path.name}))
        return 0
    except Exception as exc:
        # Do not print exception text: filesystem/SQL details may be sensitive.
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}), file=sys.stderr)
        return 1
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())
