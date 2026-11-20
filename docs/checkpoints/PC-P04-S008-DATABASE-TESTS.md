# PC-P04-S008 — Database Tests

**Test files:** tests/test_database_connection.py and tests/test_database_repository.py  
**Status:** IMPLEMENTED — GitHub Actions and Colab verification pending

Automated tests cover connection lifecycle, row mapping, foreign-key enforcement, health checks, transaction commit/rollback, project/task CRUD, dependency constraints and cycle rejection, activity JSON payloads, and cascading deletes. Tests use temporary database files and do not write to a shared project database.

Acceptance commands:

    python -m compileall -q database tests
    python -m pytest -q tests/test_database_connection.py tests/test_database_repository.py
    python -m pytest -q

Checkpoint completion remains pending until the full CI and required runtime checks pass.
