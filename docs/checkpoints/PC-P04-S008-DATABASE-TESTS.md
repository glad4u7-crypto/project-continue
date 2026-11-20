# PC-P04-S008 — Database Tests

**Test files:** tests/test_database_connection.py and tests/test_database_repository.py  
**Status:** IMPLEMENTED — GitHub CI PASS; Colab runtime retest pending

Automated tests cover connection lifecycle, row mapping, foreign-key enforcement, health checks, transaction commit/rollback, project/task CRUD, dependency constraints and cycle rejection, activity JSON payloads, and cascading deletes. Tests use temporary database files and do not write to a shared project database.

Acceptance commands:

    python -m compileall -q database tests
    python -m pytest -q tests/test_database_connection.py tests/test_database_repository.py
    python -m pytest -q

Checkpoint completion remains pending until the full CI and required runtime checks pass.


## Latest GitHub CI evidence — 2026-11-20

Main CI run #270 passed: Python 3.11.18, Gitleaks no leaks, pip-audit no known vulnerabilities, compile passed, database-marked group 21 passed, full suite 161 passed, statement coverage 95% (821 statements; 39 uncovered). Test and coverage reports uploaded successfully.

## Remaining acceptance gate

Final Colab runtime retest against the exact current main SHA remains required before this checkpoint can be marked PASS. Capture Python version, exact SHA, focused outputs, full-suite output, exit codes and the file-backed SQLite workflow evidence. GitHub CI is not represented as Colab evidence.
