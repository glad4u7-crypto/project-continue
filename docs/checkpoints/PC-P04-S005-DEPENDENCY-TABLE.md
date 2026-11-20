# PC-P04-S005 — Dependency Table

**Implementation:** database/schema.py and ProjectRepository.add_dependency/list_dependencies  
**Status:** PASS — implementation, GitHub CI, and exact-SHA Colab runtime acceptance verifiedntime retest pending

Task dependencies use a composite primary key (task_id, depends_on_task_id), foreign keys with cascading deletion, and a self-dependency CHECK constraint. Repository validation rejects self-links, missing tasks, cross-project dependencies, duplicate links, and dependency cycles. SQLite BEFORE INSERT and BEFORE UPDATE triggers independently prevent cross-project links and dependency cycles.

Acceptance: valid dependency chains persist; invalid/self/cross-project/cyclic links are rejected.


## Latest GitHub CI evidence — 2026-11-20

Main CI run #270 passed: Python 3.11.18, Gitleaks no leaks, pip-audit no known vulnerabilities, compile passed, database-marked group 21 passed, full suite 161 passed, statement coverage 95% (821 statements; 39 uncovered). Test and coverage reports uploaded successfully.


## Colab runtime acceptance — 2026-11-20

- Result: **PASS**. User-provided Colab output ended with `=== PC-P04 COLAB RUNTIME ACCEPTANCE PASSED ===`.
- Repository: `https://github.com/glad4u7-crypto/project-continue`; branch: `main`.
- Expected SHA: `50b001467e9b5d9692cb2490bce26efef497e0d2`; actual SHA: `50b001467e9b5d9692cb2490bce26efef497e0d2`; verified SHA: `50b001467e9b5d9692cb2490bce26efef497e0d2` (exact match).
- Python: `3.13.18`.
- Commands completed successfully:
  - `python -m pip install -r requirements.txt`
  - `python -m compileall -q database tests`
  - `python -m pytest -m database -q`
  - `python -m pytest -q tests/test_database_connection.py tests/test_database_repository.py`
  - `python -m pytest -q`
- The user output confirms each command returned control to the runner and the final acceptance success marker was printed. Individual pytest counts and detailed per-test output were not included in the supplied transcript and are intentionally not inferred.
- This is Colab runtime evidence, distinct from GitHub Actions CI evidence. The test suite includes file-backed persistence and backup/restore regression coverage; the supplied transcript does not show a separate manual end-to-end database workflow transcript.
