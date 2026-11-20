# PC-P04-S006 — Activity History

**Implementation:** database/schema.py and ProjectRepository.record_activity/list_activity  
**Status:** IMPLEMENTED — GitHub CI PASS; Colab runtime retest pending

Activity history stores an integer event ID, required project foreign key, optional task foreign key, event type, JSON payload, and UTC timestamp. Project deletion cascades to its history; task deletion preserves the event and nulls its task reference. Project/time and event retrieval are indexed and bounded.

Acceptance: record and retrieve JSON event payloads; reject invalid foreign-key references; verify retention behavior on task deletion and project cascade.


## Latest GitHub CI evidence — 2026-11-20

Main CI run #270 passed: Python 3.11.18, Gitleaks no leaks, pip-audit no known vulnerabilities, compile passed, database-marked group 21 passed, full suite 161 passed, statement coverage 95% (821 statements; 39 uncovered). Test and coverage reports uploaded successfully.

## Remaining acceptance gate

Final Colab runtime retest against the exact current main SHA remains required before this checkpoint can be marked PASS. Capture Python version, exact SHA, focused outputs, full-suite output, exit codes and the file-backed SQLite workflow evidence. GitHub CI is not represented as Colab evidence.
