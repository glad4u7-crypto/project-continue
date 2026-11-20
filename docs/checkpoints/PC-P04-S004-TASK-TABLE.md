# PC-P04-S004 — Task Table

**Implementation:** database/schema.py and ProjectRepository task CRUD methods  
**Status:** IMPLEMENTED — GitHub CI PASS; Colab runtime retest pending

Tasks belong to a project through a required foreign key with ON DELETE CASCADE. Each task stores title, description, priority, status, optional due timestamp, and UTC creation/update timestamps. Priority and status are constrained in SQLite and normalized/validated before writes. Project/status and project/priority indexes support common lookups.

Acceptance: create/read/list/update/delete tasks; reject missing projects and invalid priority/status; verify project deletion cascades.


## Latest GitHub CI evidence — 2026-11-20

Main CI run #270 passed: Python 3.11.18, Gitleaks no leaks, pip-audit no known vulnerabilities, compile passed, database-marked group 21 passed, full suite 161 passed, statement coverage 95% (821 statements; 39 uncovered). Test and coverage reports uploaded successfully.

## Remaining acceptance gate

Final Colab runtime retest against the exact current main SHA remains required before this checkpoint can be marked PASS. Capture Python version, exact SHA, focused outputs, full-suite output, exit codes and the file-backed SQLite workflow evidence. GitHub CI is not represented as Colab evidence.
