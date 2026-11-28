# Phase 20.4 — Ephemeral execution runner acceptance

- Repository: `glad4u7-crypto/project-continue`
- Implementation branch: `phase20/secure-dispatcher-u20-3-01`
- Date: 2026-11-28 (Asia/Kolkata)
- Status: PASS — all 10 acceptance checkpoints verified on exact code SHA `29a06b4f12bc61054af45e196f036ea480d82da1`.

## Implemented artifacts

- `.github/workflows/phase20-ephemeral-runner.yml`: GitHub-hosted ephemeral runner workflow.
- `scripts/phase20_runner.py`: fixed-task runner with no shell or caller-controlled command.
- `tests/test_phase20_runner.py`: allow-list, timeout, environment isolation, process cleanup, output bound and OS resource-limit tests.

## Checkpoint disposition (pending final CI)

| Unit | Acceptance | Implementation evidence | Status |
|---|---|---|---|
| U20-4-01 | Safe workflow trigger selected | Push to `phase20/**` and PR targeting `main`; no workflow_dispatch dependence because current connector cannot dispatch workflows | PASS |
| U20-4-02 | Minimal permissions | Workflow and job explicitly grant only `contents: read` | PASS |
| U20-4-03 | Actions pinned | checkout and setup-python use full reviewed commit SHAs | IMPLEMENTED — CI pending |
| U20-4-04 | Immutable checkout | Checkout ref is PR head SHA or push event SHA; fetch-depth 1; credentials persistence disabled | IMPLEMENTED — CI pending |
| U20-4-05 | Fixed handlers only | CLI accepts exactly compile, dispatcher-tests, full-tests; immutable argv; no shell, eval, dynamic import or caller-supplied flags | IMPLEMENTED — CI pending |
| U20-4-06 | Workspace/data isolation | GitHub-hosted job workspace is ephemeral; dedicated temporary HOME; child environment allow-listed; no persistent runner cache or production mount | IMPLEMENTED — CI pending |
| U20-4-07 | Resource bounds | 20-minute job timeout; 600-second task wall/CPU limits; process-group kill on timeout; 64 KiB retained output; core dumps disabled; no artifacts emitted/uploaded | IMPLEMENTED — CI pending |
| U20-4-08 | Cancellation/failure cleanup | concurrency group cancels superseded runs; timeout kills the process group; temporary HOME is removed by context cleanup; runner job is destroyed after completion | IMPLEMENTED — CI pending |
| U20-4-09 | No production state/credentials | read-only contents permission, checkout credentials not persisted, no secrets injected, minimal child environment, no production database/Drive mounts or deployment step | IMPLEMENTED — CI pending |
| U20-4-10 | Real run evidence | Dedicated run `46110154120`, job `140871655026`, and main CI run `46110154179`, job `140871654899`, both SUCCESS on exact SHA `29a06b4f12bc61054af45e196f036ea480d82da1` | PASS |

## Security and operational boundaries

- This runner only compiles and tests repository code. It is not yet a ChatGPT-to-runner dispatch bridge and does not execute Colab notebooks, arbitrary Python, shell, SQL, deployment, merge, or production mutations.
- Triggering uses repository push/PR events. The current ChatGPT GitHub connector has no workflow-dispatch action, so direct on-demand workflow dispatch remains unavailable.
- GitHub-hosted runner is ephemeral; the workflow uses no paid runner class, no paid API, no persistent cache, no external automation service and no production credentials.
- GitHub-hosted runner platform quotas still apply; account-level billing/minute budget cannot be inspected from the connector.
- Cancellation is tested through the process cleanup unit tests and concurrency configuration; a live operator-initiated cancellation drill is not claimed.
- Test output is bounded to 64 KiB per task. No test artifacts are uploaded by this workflow.
- The runner script uses Linux resource limits and is intended for the Ubuntu GitHub-hosted runner specified in the workflow.

## CI evidence

- Dedicated runner workflow: https://github.com/glad4u7-crypto/project-continue/actions/runs/46110154120 — SUCCESS on exact SHA `29a06b4f12bc61054af45e196f036ea480d82da1`; job `140871655026`.
- Main repository CI: https://github.com/glad4u7-crypto/project-continue/actions/runs/46110154179 — SUCCESS on the same exact SHA; job `140871654899`.
- Runner safety tests: 6 passed, 5 subtests passed.
- Fixed dispatcher acceptance suite: 53 passed, 29 subtests passed.
- Runner-executed full regression: 369 passed, 11 skipped, 34 subtests passed in 9.26s.
- Main CI full suite: 369 passed, 11 skipped, 34 subtests passed in 9.26s; coverage 79% (2,575 statements, 544 missed).
- Main CI includes secret scan, dependency audit, compile, production container build, Compose validation, smoke test, focused categories, full suite and artifact upload. Artifact ID `15249342536` (280,613 bytes; SHA-256 `bf3b97f0e76de3771a354dc89629b84f03661e3482d9f324dc4e33db5cb6bd2f`): https://github.com/glad4u7-crypto/project-continue/actions/runs/46110154179/artifacts/15249342536.

## Acceptance rule

All ten checkpoints are accepted on the exact code SHA above. The dedicated runner is a bounded compile/test runner, not yet a natural-language on-demand dispatch bridge; workflow_dispatch remains unavailable through the current connector. Live operator cancellation and cross-platform runner behavior are not claimed.
