# PC-P04-S003 — Project Table

**Implementation:** database/schema.py and ProjectRepository.create_project/get_project/list_projects/update_project/delete_project  
**Status:** IMPLEMENTED — GitHub CI PASS; Colab runtime retest pending

Projects have a stable text primary key, unique non-empty name (validated in the repository), description, active/archived status constraint, and UTC creation/update timestamps. Project records are indexed by their primary/unique keys. Project deletion cascades to dependent project data by foreign-key policy.

Acceptance: create/read/list/update/delete project records; reject duplicate IDs/names and invalid status; confirm cascade behavior.


## Latest GitHub CI evidence — 2026-11-20

Main CI run #270 passed: Python 3.11.18, Gitleaks no leaks, pip-audit no known vulnerabilities, compile passed, database-marked group 21 passed, full suite 161 passed, statement coverage 95% (821 statements; 39 uncovered). Test and coverage reports uploaded successfully.

## Remaining acceptance gate

Final Colab runtime retest against the exact current main SHA remains required before this checkpoint can be marked PASS. Capture Python version, exact SHA, focused outputs, full-suite output, exit codes and the file-backed SQLite workflow evidence. GitHub CI is not represented as Colab evidence.
