"""Read-only runtime diagnostics for the Streamlit dashboard."""
from __future__ import annotations

from datetime import datetime, timezone

from database.connection import Database
from database.schema import SCHEMA_VERSION

REQUIRED_TABLES = {
    "schema_version",
    "projects",
    "tasks",
    "task_dependencies",
    "activity_history",
}


def run_self_check(repository, settings) -> dict[str, object]:
    """Inspect runtime readiness without inserting, updating, or deleting data.

    Returned values are deliberately limited to safe operational metadata.
    Database paths, project names, task contents, credentials, and SQL errors
    are never returned.
    """
    database = repository.database
    checks: list[dict[str, str]] = []

    try:
        database_ok = bool(database.health_check())
    except Exception:
        database_ok = False
    checks.append({
        "check": "Database connection",
        "status": "PASS" if database_ok else "FAIL",
        "detail": "Database answered a health query." if database_ok else "Database health query failed.",
    })

    if isinstance(database, Database) and database_ok:
        try:
            with database.connection() as connection:
                present = {
                    row["name"]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                missing = REQUIRED_TABLES - present
                schema_ok = not missing
                version_row = connection.execute(
                    "SELECT version FROM schema_version WHERE id=1"
                ).fetchone() if "schema_version" in present else None
                version_ok = version_row is not None and version_row["version"] >= SCHEMA_VERSION
                integrity_row = connection.execute("PRAGMA integrity_check").fetchone()
                integrity_ok = integrity_row is not None and integrity_row[0] == "ok"
                foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
                foreign_keys_ok = not foreign_key_errors
            checks.extend([
                {
                    "check": "Required database tables",
                    "status": "PASS" if schema_ok else "FAIL",
                    "detail": "All required tables are present." if schema_ok else "One or more required tables are missing.",
                },
                {
                    "check": "Schema version",
                    "status": "PASS" if version_ok else "FAIL",
                    "detail": "Database schema is current." if version_ok else "Database schema version needs attention.",
                },
                {
                    "check": "SQLite integrity",
                    "status": "PASS" if integrity_ok else "FAIL",
                    "detail": "SQLite integrity check passed." if integrity_ok else "SQLite integrity check failed.",
                },
                {
                    "check": "Foreign-key consistency",
                    "status": "PASS" if foreign_keys_ok else "FAIL",
                    "detail": "No foreign-key violations found." if foreign_keys_ok else "Foreign-key violations found.",
                },
            ])
        except Exception:
            checks.append({
                "check": "Database structure and integrity",
                "status": "FAIL",
                "detail": "A read-only database diagnostic could not complete.",
            })
    else:
        checks.append({
            "check": "SQLite structure and integrity",
            "status": "SKIP",
            "detail": "Detailed SQLite checks are unavailable for this database adapter or connection.",
        })

    github_configured = bool(getattr(settings, "github_repository", "").strip())
    checks.append({
        "check": "GitHub integration configuration",
        "status": "PASS" if github_configured else "WARN",
        "detail": "A repository is configured." if github_configured else "GITHUB_REPOSITORY is not configured.",
    })

    app_env = getattr(settings, "app_env", "unknown")
    checks.append({
        "check": "Application environment",
        "status": "PASS" if app_env in {"development", "test", "production"} else "WARN",
        "detail": f"Application environment: {app_env}.",
    })

    failed = sum(item["status"] == "FAIL" for item in checks)
    warnings = sum(item["status"] == "WARN" for item in checks)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall": "FAIL" if failed else ("WARN" if warnings else "PASS"),
        "summary": {"passed": sum(x["status"] == "PASS" for x in checks),
                    "failed": failed, "warnings": warnings,
                    "skipped": sum(x["status"] == "SKIP" for x in checks)},
        "checks": checks,
    }
