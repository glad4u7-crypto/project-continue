# PC-P04-S003 — Project Table

**Implementation:** database/schema.py and ProjectRepository.create_project/get_project/list_projects/update_project/delete_project  
**Status:** PASS — implementation, GitHub CI, and exact-SHA Colab runtime acceptance verifiedntime retest pending

Projects have a stable text primary key, unique non-empty name (validated in the repository), description, active/archived status constraint, and UTC creation/update timestamps. Project records are indexed by their primary/unique keys. Project deletion cascades to dependent project data by foreign-key policy.

Acceptance: create/read/list/update/delete project records; reject duplicate IDs/names and invalid status; confirm cascade behavior.


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
