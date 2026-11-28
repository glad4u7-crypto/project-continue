# Phase 20.6 — Python compile, unit test and debugging acceptance

**Date:** 2026-11-28 (Asia/Kolkata)  
**Repository:** `glad4u7-crypto/project-continue`  
**Branch:** `phase20/secure-dispatcher-u20-3-01`  
**Verified code SHA:** `2ff748243837ab3f99898c173779d3f8cdb868ec`  
**PR:** #71 — Draft, not merged  
**Result:** PASS — U20-6-01 through U20-6-11 have evidence-backed dispositions; U20-6-05 is PASS by documented not-applicable assessment.

## Checkpoint evidence

| Unit | Result | Evidence |
|---|---|---|
| U20-6-01 Python/dependency baseline | PASS | CPython 3.11, dependency ranges, pytest configuration and absence of a full transitive lockfile documented in `2026-11-28-U20-6-01-Python-Dependency-Baseline.md`. |
| U20-6-02 compile handler | PASS | Fixed `compile` allow-listed task executed successfully in run [46122965873](https://github.com/glad4u7-crypto/project-continue/actions/runs/46122965873). |
| U20-6-03 focused pytest handler | PASS | Fixed `dispatcher-tests` allow-list; 69 passed, 47 subtests passed in run 46122965873. |
| U20-6-04 full pytest handler | PASS | Fixed `full-tests`; 391 passed, 11 skipped, 52 subtests passed in run 46122965873. |
| U20-6-05 lint/type-check applicability | PASS (not applicable) | Inspected repository configuration: no Ruff, Flake8, mypy, pyright, tox, pre-commit or equivalent lint/type-check configuration/handler is established. No new tool/dependency was introduced; compile + tests + pip-audit remain the configured checks. This is an applicability decision, not a claim that a linter ran. |
| U20-6-06 structured output capture | PASS | `phase20_runner.py` captures stdout/stderr separately, bounded to 64 KiB per stream, byte totals/truncation, exit code, timeout, duration and parsed pytest counts. A real child-process test proves stdout/stderr separation. Runner run 46122965873 emitted machine-readable ATTEMPT/RESULT JSON. |
| U20-6-07 failure classification | PASS | Unit tests cover success, timeout, permission, dependency, code and infrastructure/environment classification paths; see `tests/test_phase20_runner.py`. |
| U20-6-08 intentional failure detection | PASS | Synthetic intentional pytest-failure transcript containing a failing test node and AssertionError is classified as `code`; classification test is included in runner safety suite. This tests detection without adding a permanently failing test to normal collection. |
| U20-6-09 feature-branch patch | PASS | Runner, tests and workflow fixes committed only to feature branch. Latest verified code SHA above; no main write. |
| U20-6-10 exact-SHA retest | PASS | Dedicated runner, main CI and associated acceptance workflows ran against exact code SHA `2ff748243837ab3f99898c173779d3f8cdb868ec`; all required runs completed successfully. |
| U20-6-11 bounded retry | PASS | Retry ceiling is one; only infrastructure-classified failures are retried. Unit tests prove one retry on transient infrastructure failure and no retry on code/test failure. CI invokes `--retry-transient`; machine-readable result records attempts and retry limit. |

## CI evidence — exact code SHA

- [Phase 20 Ephemeral Fixed-Task Runner — run 46122965873](https://github.com/glad4u7-crypto/project-continue/actions/runs/46122965873): SUCCESS. Runner safety suite: 12 passed, 5 subtests passed; compile PASS; dispatcher suite 69 passed, 47 subtests; full regression 391 passed, 11 skipped, 52 subtests.
- [Project Continue CI — run 46122965859](https://github.com/glad4u7-crypto/project-continue/actions/runs/46122965859): SUCCESS. Full regression 391 passed, 11 skipped, 52 subtests; coverage reports generated.
- [PostgreSQL integration — run 46122965932](https://github.com/glad4u7-crypto/project-continue/actions/runs/46122965932): SUCCESS; PostgreSQL-enabled test suite reported 402 passed, 52 subtests.
- [Dashboard Browser Acceptance — run 46122965838](https://github.com/glad4u7-crypto/project-continue/actions/runs/46122965838): SUCCESS.
- [Phase 14 Production Operations — run 46122965892](https://github.com/glad4u7-crypto/project-continue/actions/runs/46122965892): SUCCESS.
- [Cloud Acceptance Lab — run 46122965866](https://github.com/glad4u7-crypto/project-continue/actions/runs/46122965866): SUCCESS.
- [Phase 13 Memory and Checkpoint Engine — run 46122965856](https://github.com/glad4u7-crypto/project-continue/actions/runs/46122965856): SUCCESS.

All listed runs target the same code SHA. Earlier failed runs remain in GitHub Actions history and are not counted as passing evidence; the pytest-summary parser was corrected before these successful runs.

## Explicit limitations

- The 11 skips in the no-DSN main CI run are opt-in PostgreSQL tests; the separate PostgreSQL integration workflow passed.
- U20-6-05 is an applicability PASS only; no lint/type-check tool is configured or claimed.
- U20-6-08 uses a synthetic failing pytest transcript for safe classification testing; it does not add or run a permanently failing test in the repository's normal test suite.
- The repository has bounded dependency ranges but no full transitive lockfile (documented in U20-6-01).
- PR #71 remains Draft and unmerged. Main branch and production data were not changed.

**Exit gate:** U20-6-01..11 = 11/11 PASS (including explicit not-applicable assessment for U20-6-05). Phase 20.6 is complete; next planned parent phase is 20.7 — Notebook inventory, create, read and execute.