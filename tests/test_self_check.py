from types import SimpleNamespace

from database import Database, ProjectRepository
from services.self_check import run_self_check


def test_self_check_passes_for_initialized_isolated_database(tmp_path):
    database = Database(tmp_path / "self-check.sqlite3")
    repository = ProjectRepository(database)
    repository.initialize()
    settings = SimpleNamespace(app_env="test", github_repository="owner/repo")

    report = run_self_check(repository, settings)

    assert report["overall"] == "PASS"
    assert report["summary"]["failed"] == 0
    assert all(item["status"] == "PASS" for item in report["checks"])
    rendered = repr(report)
    assert str(tmp_path) not in rendered
    assert "self-check.sqlite3" not in rendered
    database.close()


def test_self_check_warns_when_github_repository_is_not_configured(tmp_path):
    database = Database(tmp_path / "self-check.sqlite3")
    repository = ProjectRepository(database)
    repository.initialize()
    settings = SimpleNamespace(app_env="development", github_repository="")

    report = run_self_check(repository, settings)

    assert report["overall"] == "WARN"
    github = next(item for item in report["checks"] if item["check"] == "GitHub integration configuration")
    assert github["status"] == "WARN"
    database.close()
