# Phase 20.4 — Ephemeral execution runner acceptance

- Repository: `glad4u7-crypto/project-continue`
- Implementation branch: `phase20/secure-dispatcher-u20-3-01`
- Date: 2026-11-28 (Asia/Kolkata)
- Status: IMPLEMENTED — final CI and runner acceptance pending; no unit is PASS until the latest exact-SHA run is green.

## Implemented artifacts

- `.github/workflows/phase20-ephemeral-runner.yml`: GitHub-hosted ephemeral runner workflow.
- `scripts/phase20_runner.py`: fixed-task runner with no shell or caller-controlled command.
- `tests/test_phase20_runner.py`: allow-list, timeout, environment isolation, process cleanup, output bound and OS resource-limit tests.

## Checkpoint disposition (pending final CI)

| Unit | Acceptance | Implementation evidence | Status |
|---|---|---|---|
| U20-4-01 | Safe workflow trigger selected | Push to `phase20/**` and PR targeting `main`; no workflow_dispatch dependence because current connector cannot dispatch workflows | IMPLEMENTED — CI pending |
| U20-4-02 | Minimal permissions | Workflow and job explicitly grant only `contents: read` | IMPLEMENTED — CI pending |
| U20-4-03 | Actions pinned | checkout and setup-python use full reviewed commit SHAs | IMPLEMENTED — CI pending |
| U20-4-04 | Immutable checkout | Checkout ref is PR head SHA or push event SHA; fetch-depth 1; credentials persistence disabled | IMPLEMENTED — CI pending |
| U20-4-05 | Fixed handlers only | CLI accepts exactly compile, dispatcher-tests, full-tests; immutable argv; no shell, eval, dynamic import or caller-supplied flags | IMPLEMENTED — CI pending |
| U20-4-06 | Workspace/data isolation | GitHub-hosted job workspace is ephemeral; dedicated temporary HOME; child environment allow-listed; no persistent runner cache or production mount | IMPLEMENTED — CI pending |
| U20-4-07 | Resource bounds | 20-minute job timeout; 600-second task wall/CPU limits; process-group kill on timeout; 64 KiB retained output; core dumps disabled; no artifacts emitted/uploaded | IMPLEMENTED — CI pending |
| U20-4-08 | Cancellation/failure cleanup | concurrency group cancels superseded runs; timeout kills the process group; temporary HOME is removed by context cleanup; runner job is destroyed after completion | IMPLEMENTED — CI pending |
| U20-4-09 | No production state/credentials | read-only contents permission, checkout credentials not persisted, no secrets injected, minimal child environment, no production database/Drive mounts or deployment step | IMPLEMENTED — CI pending |
| U20-4-10 | Real run evidence | Latest workflow run must finish on exact final commit SHA; run/job URL and result will be added after completion | PENDING |

## Security and operational boundaries

- This runner only compiles and tests repository code. It is not yet a ChatGPT-to-runner dispatch bridge and does not execute Colab notebooks, arbitrary Python, shell, SQL, deployment, merge, or production mutations.
- Triggering uses repository push/PR events. The current ChatGPT GitHub connector has no workflow-dispatch action, so direct on-demand workflow dispatch remains unavailable.
- GitHub-hosted runner is ephemeral; the workflow uses no paid runner class, no paid API, no persistent cache, no external automation service and no production credentials.
- GitHub-hosted runner platform quotas still apply; account-level billing/minute budget cannot be inspected from the connector.
- Cancellation is tested through the process cleanup unit tests and concurrency configuration; a live operator-initiated cancellation drill is not claimed.
- Test output is bounded to 64 KiB per task. No test artifacts are uploaded by this workflow.
- The runner script uses Linux resource limits and is intended for the Ubuntu GitHub-hosted runner specified in the workflow.

## CI evidence

Pending final exact-SHA CI and runner workflow. Earlier initial runner workflow run `46110005482` succeeded on pre-hardening commit `c4bdf96d5d761d7594f0e555f0d37eba608b157f`; it is historical implementation evidence only and does not close the final acceptance.

## Acceptance rule

U20-4-01 through U20-4-10 will be marked PASS only after the latest commit passes both the main repository CI and this dedicated ephemeral-runner workflow, all runner-specific tests pass, source and report are read back, and the exact run/job IDs are recorded.
