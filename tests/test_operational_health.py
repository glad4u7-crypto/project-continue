from database import Database
from services.operational_health import operational_health


def test_health_reports_ready_without_leaking_database_path(tmp_path):
    db = Database(tmp_path / "private-location.sqlite3")
    result = operational_health(db)
    assert result == {"status": "ready", "database": "ok", "ready": True}
    assert "private-location" not in repr(result)
    db.close()
