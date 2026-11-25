import pytest

from database.postgres_connection import PostgresDatabase


def test_postgres_database_requires_non_empty_dsn():
    with pytest.raises(ValueError, match="DSN"):
        PostgresDatabase("")


@pytest.mark.parametrize("timeout", [0, -1, 61])
def test_postgres_database_rejects_invalid_connect_timeout(timeout):
    with pytest.raises(ValueError, match="connect_timeout"):
        PostgresDatabase("postgresql://user:pass@localhost/db", connect_timeout=timeout)


def test_postgres_database_accepts_dsn_without_connecting():
    database = PostgresDatabase("postgresql://user:pass@localhost/db")
    assert database.dsn == "postgresql://user:pass@localhost/db"
    assert database.connect_timeout == 10
