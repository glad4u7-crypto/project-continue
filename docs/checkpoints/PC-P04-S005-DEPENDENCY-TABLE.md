# PC-P04-S005 — Dependency Table

**Implementation:** database/schema.py and ProjectRepository.add_dependency/list_dependencies  
**Status:** IMPLEMENTED — GitHub CI PASS; Colab runtime retest pending

Task dependencies use a composite primary key (task_id, depends_on_task_id), foreign keys with cascading deletion, and a self-dependency CHECK constraint. Repository validation rejects self-links, missing tasks, cross-project dependencies, duplicate links, and dependency cycles. SQLite BEFORE INSERT and BEFORE UPDATE triggers independently prevent cross-project links and dependency cycles.

Acceptance: valid dependency chains persist; invalid/self/cross-project/cyclic links are rejected.


## Latest GitHub CI evidence — 2026-11-20

Main CI run #270 passed: Python 3.11.18, Gitleaks no leaks, pip-audit no known vulnerabilities, compile passed, database-marked group 21 passed, full suite 161 passed, statement coverage 95% (821 statements; 39 uncovered). Test and coverage reports uploaded successfully.

## Remaining acceptance gate

Final Colab runtime retest against the exact current main SHA remains required before this checkpoint can be marked PASS. Capture Python version, exact SHA, focused outputs, full-suite output, exit codes and the file-backed SQLite workflow evidence. GitHub CI is not represented as Colab evidence.
