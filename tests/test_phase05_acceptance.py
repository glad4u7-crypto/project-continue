from scripts.phase05_acceptance import run_acceptance


def test_phase05_file_backed_acceptance_workflow():
    assert run_acceptance() == [
        "project registration and persistence",
        "task-derived progress and status breakdown",
        "metadata update and activity history",
        "archive, filtering, and restore",
        "reopen persistence and SQLite integrity_check",
    ]
