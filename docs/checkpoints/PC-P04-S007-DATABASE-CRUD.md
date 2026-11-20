# PC-P04-S007 — Database CRUD

**Implementation:** database/repository.py — ProjectRepository  
**Status:** IMPLEMENTED — GitHub CI PASS; Colab runtime retest pending

The repository provides parameterized create/read/list/update/delete operations for projects and tasks, plus dependency and activity-history operations. Domain values pass through existing core validators. Writes use explicit transactions; dynamic UPDATE column names are selected only from fixed internal allowlists. Dependency insertion checks project boundaries and recursive reachability to prevent cycles.

Acceptance: CRUD operations pass, missing records and integrity violations fail predictably, and transaction rollback prevents partial writes.


## Latest GitHub CI evidence — 2026-11-20

Main CI run #270 passed: Python 3.11.18, Gitleaks no leaks, pip-audit no known vulnerabilities, compile passed, database-marked group 21 passed, full suite 161 passed, statement coverage 95% (821 statements; 39 uncovered). Test and coverage reports uploaded successfully.

## Remaining acceptance gate

Final Colab runtime retest against the exact current main SHA remains required before this checkpoint can be marked PASS. Capture Python version, exact SHA, focused outputs, full-suite output, exit codes and the file-backed SQLite workflow evidence. GitHub CI is not represented as Colab evidence.
