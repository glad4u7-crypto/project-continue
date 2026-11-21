"""Non-sensitive operational health and readiness checks."""
from __future__ import annotations

from database.connection import Database


def operational_health(database: Database) -> dict[str, object]:
    """Return booleans only; never expose paths, SQL errors, credentials or records."""
    try:
        db_ok = bool(database.health_check())
    except Exception:
        db_ok = False
    return {
        "status": "ready" if db_ok else "not_ready",
        "database": "ok" if db_ok else "unavailable",
        "ready": db_ok,
    }
