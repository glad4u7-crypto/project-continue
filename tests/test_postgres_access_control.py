from services.postgres_access_control import AccessDenied, PostgresAccessControl


def test_postgres_access_control_exposes_identity_and_authorization_contract():
    expected = {
        "create_user", "authenticate", "verify_principal", "issue_session",
        "verify_session", "bootstrap_project_owner", "grant_project",
        "require_project", "list_audit_events",
    }
    assert expected.issubset(set(dir(PostgresAccessControl)))
    assert issubclass(AccessDenied, PermissionError)


def test_postgres_access_control_uses_postgresql_sql_not_sqlite_dialect():
    import inspect
    source = inspect.getsource(PostgresAccessControl)
    assert "%s" in source
    assert "ON CONFLICT" in source
    assert "PRAGMA" not in source
    assert "INSERT OR IGNORE" not in source
