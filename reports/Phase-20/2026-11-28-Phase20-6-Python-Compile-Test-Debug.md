# Phase 20.6 — Python compile, unit test and debugging

- Repository: glad4u7-crypto/project-continue
- Implementation branch: phase20/u20-6-python-test-debug
- Date: 2026-11-28 (Asia/Kolkata)
- Status: PASS — 11/11 checkpoints verified
- Exact tested code SHA: 014703741d2c4b50f433967a41757bb0d319cb5c
- Draft PR: https://github.com/glad4u7-crypto/project-continue/pull/72 (stacked on Phase 20.5 branch; not merged)

## Implementation

- scripts/phase20_test_harness.py: immutable task registry for baseline, compile, focused, full, optional lint, and failure-probe.
- tests/test_phase20_test_harness.py: task allow-list, structured counts, output redaction/bounds, failure classification, one-retry policy, retry exhaustion/BLOCKED, and no-retry-on-code-failure tests.
- .github/workflows/phase20-ephemeral-runner.yml: exact event-SHA checkout, minimal read-only permissions, and execution of the harness steps.
- Results are JSON with separate stdout/stderr, exit code, duration, pytest counts, attempts, failure class, and retryability. Output is bounded to 32 KiB per stream and common credential patterns are redacted.

## Checkpoint acceptance

| Unit | Acceptance | Evidence | Status |
|---|---|---|---|
| U20-6-01 | Python version and dependency baseline | Python 3.11.18; resolved installed package inventory captured in dedicated runner logs. requirements.txt has bounded ranges; no lockfile exists. | PASS |
| U20-6-02 | Compile-only handler | Fixed compile task compiled app/config/core/database/integrations/services/src/scripts/tests. | PASS |
| U20-6-03 | Focused pytest handler | 85 passed, 52 subtests passed. | PASS |
| U20-6-04 | Full pytest handler | 395 passed, 11 skipped, 52 subtests passed in 10.507s. | PASS |
| U20-6-05 | Optional lint/type check | Ruff is not installed and no lint/type-check config exists; optional task explicitly returns SKIPPED without adding a dependency. | PASS — N/A |
| U20-6-06 | Output/result collection | Separate stdout/stderr, exit code, monotonic duration, test counts, attempts and retryability returned as structured JSON. | PASS |
| U20-6-07 | Failure classification | Code, environment, dependency, permission, timeout and infrastructure classes covered. | PASS |
| U20-6-08 | Intentional failure detection | Deliberate AssertionError returned EXPECTED_FAILURE_DETECTED and intentional-code-failure; expected probe did not fail the workflow. | PASS |
| U20-6-09 | Feature-branch patch and commit | Changes committed on phase20/u20-6-python-test-debug; Draft PR #72 opened against Phase 20.5 branch. | PASS |
| U20-6-10 | Exact-SHA retest | Dedicated runner, main CI push, PR CI and Phase 14 compatibility workflow all passed on exact SHA 014703741d2c4b50f433967a41757bb0d319cb5c. | PASS |
| U20-6-11 | Bounded retry and BLOCKED handling | Maximum one retry; transient failure retries once; repeated transient failure returns BLOCKED; code failure is not retried. | PASS |

## CI evidence on exact SHA

- Dedicated fixed-task runner: https://github.com/glad4u7-crypto/project-continue/actions/runs/46112817942 — SUCCESS; job 140879918518.
- Main repository CI (push): https://github.com/glad4u7-crypto/project-continue/actions/runs/46112817976 — SUCCESS.
- Main repository CI (PR): https://github.com/glad4u7-crypto/project-continue/actions/runs/46112838101 — SUCCESS.
- Phase 14 compatibility workflow: https://github.com/glad4u7-crypto/project-continue/actions/runs/46112838067 — SUCCESS.
- Python: 3.11.18.
- Focused test harness + runner tests: 85 passed, 52 subtests passed.
- Full regression: 395 passed, 11 skipped, 52 subtests passed.
- Compile, secret scan, dependency audit, production container build, Compose validation and container smoke test: SUCCESS in main CI.
- Intentional failure probe: correctly detected.
- Optional lint: SKIPPED because Ruff is not installed; no new package dependency was introduced.

## Debugging history (preserved)

- Run 46112356846: first test run exposed incorrect pytest summary regex escaping; corrected.
- Run 46112425722: exposed singular error summary parsing; corrected to accept singular/plural.
- Run 46112506305: exposed quoting in the Python/dependency baseline command; corrected.
- Run 46112783834: exposed a malformed comment/newline edit during classifier clarification; corrected.
- Subsequent exact-SHA validation on 014703741d2c4b50f433967a41757bb0d319cb5c passed. Failed runs were not erased or reclassified.

## Limitations and safety

- requirements.txt specifies bounded version ranges rather than exact pins; no lockfile exists. Runtime package inventory is captured as a baseline, not claimed as lockfile reproducibility.
- PostgreSQL-dependent tests (11) remain skipped because dedicated test DSNs were not configured. They are not counted as PASS.
- Ruff lint is not installed; no lint pass is claimed.
- A separate dashboard-health.yml push run failed without a job record. It is not part of the Phase 20.6 acceptance workflow; main CI, dedicated runner, PR CI and Phase 14 compatibility checks all passed.
- PR #72 remains DRAFT, stacked on PR #71. PR #71 also remains DRAFT. No main merge, deployment, production database change, credential change or live service restart occurred.

## Rollback

Close Draft PR #72; no main-branch changes have occurred. PR #71 remains a separate unmerged Draft.
