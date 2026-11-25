from database.postgres_repository import PostgresProjectRepository


def test_postgres_repository_exposes_existing_project_task_contract():
    expected = {
        "initialize", "create_project", "get_project", "list_projects",
        "update_project", "delete_project", "create_task", "get_task",
        "list_tasks", "update_task", "delete_task", "add_dependency",
        "remove_dependency", "list_dependencies", "record_activity", "list_activity",
    }
    assert expected.issubset(set(dir(PostgresProjectRepository)))


def test_postgres_repository_uses_postgresql_parameter_and_returning_syntax():
    import inspect
    source = inspect.getsource(PostgresProjectRepository)
    assert "%s" in source
    assert "RETURNING id" in source
    assert "lastrowid" not in source
    assert "PRAGMA" not in source
