# U20-3-06 — Malformed, expired, duplicate and replayed request rejection

- Repository: `glad4u7-crypto/project-continue`
- Branch: `phase20/secure-dispatcher-u20-3-01`
- Date: 2026-11-28 (Asia/Kolkata)
- Disposition: IMPLEMENTED — 11-TEST CI PASS; FINAL 13-TEST CI PENDING

## Implemented

- `src/dispatcher/request_guard.py`: strict envelope shape, UUID request ID and nonce, actor/repository/commit/task shape checks, timezone-aware timestamp parsing, future/expired/invalid lifetime and maximum-TTL checks. `RequestGuard` provides a reusable fail-closed boundary and calls the replay store before a caller resolves or invokes a task handler.
- `src/dispatcher/replay_store.py`: durable SQLite replay store using the repository's existing `Database` transaction manager. It creates a namespaced primary-key table, expires stale rows, and atomically claims request ID + nonce. If either value collides, a deliberate rollback prevents partial consumption. Storage errors propagate (fail closed).
- `tests/test_dispatcher_request_guard.py`: 13 deterministic unittest cases cover valid and malformed requests, timestamp and TTL rules, duplicate/replay rejection, fail-closed store errors, replay-store contract validation, guard-to-store integration, durable duplicate detection, rollback of partial claims, and expiry cleanup.
- `.github/workflows/ci.yml`: added `phase20/**` to the push-trigger branch filter. Evidence-only changes under `reports/**` are ignored to avoid unnecessary full container builds and conserve free GitHub Actions minutes.

## Storage and deployment constraints

- SQLite is already a supported application backend. The replay store must use the same durable database file as the dispatcher and that file must be on persistent storage shared by every worker that can receive the same requests.
- Do not use SQLite `:memory:`, ephemeral runner storage, or separate per-worker database files for production replay protection.
- `RequestGuard` is now an explicit reusable validation boundary, but there is not yet an application dispatcher handler lookup/runtime entrypoint that invokes it and combines it with U20-3-05 authenticated identity, repository permission and commit-SHA verification. End-to-end runtime enforcement is not claimed.

## CI evidence

- Earlier full CI run (11-test version): https://github.com/glad4u7-crypto/project-continue/actions/runs/46098486057 — **SUCCESS**. Secret scan, dependency installation/audit, Python compile, Docker build, Compose validation, production-container health smoke test, focused test categories, and complete pytest suite all completed successfully.
- Final CI run for the 13-test version and final workflow: https://github.com/glad4u7-crypto/project-continue/actions/runs/46098670631 — queued/in progress at the time of this report. Its result must be checked before changing this unit to PASS.
- Final source/test files must be read back from the target branch and their SHAs recorded after CI completion.

## Remaining acceptance gates

1. Final CI run 46098670631 must complete successfully, including compile, focused tests, complete pytest suite, container build and smoke test.
2. If CI fails, inspect job logs, fix the cause, and rerun.
3. A later dispatcher runtime entrypoint must call `RequestGuard.validate()` before handler lookup and combine it with U20-3-05 authenticated actor/repository/commit authorization.
4. Read back the final implementation, tests, workflow and report from the branch and record their SHAs.

No merge to main and no live service/data modification.
