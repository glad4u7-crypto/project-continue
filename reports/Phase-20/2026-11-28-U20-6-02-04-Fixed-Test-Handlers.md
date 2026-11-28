# U20-6-02 to U20-6-04 — Fixed compile and pytest task handlers

**Date:** 2026-11-28 (Asia/Kolkata)  
**Repository:** `glad4u7-crypto/project-continue`  
**Branch:** `phase20/secure-dispatcher-u20-3-01`  
**Verified code commit:** `cf6e342badd589f572ae05afecb64af2253ba58e`  
**Current PR head at verification:** documentation-only descendants of the verified code commit  
**Status:** PASS — three fixed task handlers and real execution evidence verified

## Existing fixed task registry

The repository-owned `scripts/phase20_runner.py` implements a strict task allow-list in `build_command`:

- `compile`: invokes the current Python interpreter with `-m compileall -q` over the fixed application, service, dispatcher and test paths.
- `dispatcher-tests`: invokes `python -m pytest -q` with the immutable `_DISPATCHER_TESTS` path tuple.
- `full-tests`: invokes `python -m pytest -q` with no caller-controlled arguments.

Unknown task strings raise `ValueError`. The runner uses `shell=False`; no caller-supplied command, path, interpreter flag or pytest argument is accepted.

## Automated safety tests

`tests/test_phase20_runner.py` verifies:
- only the three exact task IDs are accepted;
- arbitrary command strings and path-like task values are rejected;
- the focused test command uses only the fixed dispatcher test list;
- the compile handler runs through the fixed command builder;
- the full suite task is allow-listed;
- process execution has a bounded timeout and minimal environment.

## Real GitHub Actions evidence

The dedicated Phase 20 runner executed all three handlers on exact code SHA `cf6e342badd589f572ae05afecb64af2253ba58e`:

- [Dedicated runner run 46111096475](https://github.com/glad4u7-crypto/project-continue/actions/runs/46111096475) — SUCCESS.
- [Main CI run 46111096455](https://github.com/glad4u7-crypto/project-continue/actions/runs/46111096455) — SUCCESS.
- Dedicated runner workflow: `.github/workflows/phase20-ephemeral-runner.yml`.
- Runner test suite: `tests/test_phase20_runner.py`.
- Dispatcher acceptance and full regression handlers both completed in the dedicated workflow.

The progress tracker records the same exact code SHA and results: 385 passed, 11 PostgreSQL tests skipped in the no-DSN main job, 52 subtests, 79% coverage. The separate PostgreSQL integration workflow from the Phase 20.5 report remains the evidence for PostgreSQL-specific tests.

## Checkpoint decisions

- **U20-6-02 — PASS:** compile-only fixed task handler exists, is allow-listed, safety-tested and executed in the dedicated workflow.
- **U20-6-03 — PASS:** focused pytest handler exists with a fixed test-file allow-list and was executed in the dedicated workflow.
- **U20-6-04 — PASS:** full pytest handler exists and the full regression suite completed successfully in the dedicated workflow.

## Scope boundary

These checkpoints establish compile/focused/full test task handlers and their execution. They do **not** establish separate stdout/stderr capture, duration/test-count metadata, failure classification, intentional-failure detection, patch-and-retest automation or bounded debugging retries. Those remain U20-6-06 through U20-6-11. No main-branch write or merge occurred.
