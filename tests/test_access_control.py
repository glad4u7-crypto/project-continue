import pytest
import sqlite3

from database import Database, ProjectRepository
from services.access_control import AccessControl, AccessDenied


@pytest.fixture
def access(tmp_path):
    db = Database(tmp_path / "isolated.sqlite3")
    repo = ProjectRepository(db)
    repo.initialize()
    repo.create_project("p-1", "One")
    repo.create_project("p-2", "Two")
    service = AccessControl(db, b"x" * 48)
    service.create_user("owner-1", "owner@example.test", "correct horse battery", role="owner")
    service.create_user("viewer-1", "viewer@example.test", "correct horse battery", role="viewer")
    service.create_user("admin-1", "admin@example.test", "correct horse battery", role="admin")
    yield service
    db.close()


def test_password_authentication_and_non_disclosure(access):
    assert access.authenticate("OWNER@example.test", "correct horse battery")["id"] == "owner-1"
    assert access.authenticate("owner@example.test", "incorrect password") is None
    assert access.authenticate("missing@example.test", "incorrect password") is None


def test_signed_session_round_trip_and_tamper_rejection(access):
    principal = access.authenticate("owner@example.test", "correct horse battery")
    token = access.issue_session(principal)
    assert access.verify_session(token)["id"] == "owner-1"
    assert access.verify_session(token + "tampered") is None


def test_session_signing_key_must_be_strong(access):
    with pytest.raises(ValueError, match="32 bytes"):
        AccessControl(access.database, "short")


def test_project_membership_enforces_read_write_manage(access):
    owner = access.authenticate("owner@example.test", "correct horse battery")
    viewer = access.authenticate("viewer@example.test", "correct horse battery")
    access.bootstrap_project_owner(owner, "p-1")
    access.grant_project(owner, "p-1", "viewer-1", role="viewer")
    access.require_project(viewer, "p-1", permission="read")
    with pytest.raises(AccessDenied):
        access.require_project(viewer, "p-1", permission="write")
    with pytest.raises(AccessDenied):
        access.require_project(viewer, "p-1", permission="manage")


def test_cross_project_access_is_denied(access):
    owner = access.authenticate("owner@example.test", "correct horse battery")
    with pytest.raises(AccessDenied):
        access.require_project(owner, "p-2", permission="read")


def test_admin_can_manage_existing_projects(access):
    admin = access.authenticate("admin@example.test", "correct horse battery")
    access.require_project(admin, "p-1", permission="manage")
    access.require_project(admin, "p-2", permission="write")


def test_access_decisions_are_audited_without_secrets(access):
    owner = access.authenticate("owner@example.test", "correct horse battery")
    with pytest.raises(AccessDenied):
        access.require_project(owner, "p-2")
    events = access.list_audit_events()
    assert events[-1]["outcome"] == "denied"
    assert "correct horse battery" not in repr(events)


def test_failed_login_attempts_are_throttled_and_window_expires(tmp_path):
    now = [10000]
    db = Database(tmp_path / "throttle.sqlite3")
    ProjectRepository(db).initialize()
    access = AccessControl(db, b"z" * 48, clock=lambda: now[0])
    access.create_user("u1", "u1@example.test", "correct horse battery")
    for _ in range(10):
        assert access.authenticate("u1@example.test", "wrong password") is None
    assert access.authenticate("u1@example.test", "correct horse battery") is None
    now[0] += 901
    assert access.authenticate("u1@example.test", "correct horse battery")["id"] == "u1"
    db.close()

def test_audit_records_are_immutable(access):
    owner = access.authenticate("owner@example.test", "correct horse battery")
    with pytest.raises(AccessDenied):
        access.require_project(owner, "p-2")
    event_id = access.list_audit_events()[0]["id"]
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        with access.database.transaction() as connection:
            connection.execute("UPDATE pc_audit_events SET outcome='success' WHERE id=?", (event_id,))
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        with access.database.transaction() as connection:
            connection.execute("DELETE FROM pc_audit_events WHERE id=?", (event_id,))
