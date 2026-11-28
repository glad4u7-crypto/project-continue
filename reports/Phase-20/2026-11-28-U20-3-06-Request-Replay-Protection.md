# U20-3-06 — Malformed, expired, duplicate and replayed request rejection

- Repository: `glad4u7-crypto/project-continue`
- Branch: `phase20/secure-dispatcher-u20-3-01`
- Date: 2026-11-28 (Asia/Kolkata)
- Disposition: IMPLEMENTED — CI VERIFICATION RUNNING; NOT PASS YET

## Implemented

- `src/dispatcher/request_guard.py`: strict envelope shape, UUID request ID and nonce, actor/repository/commit/task shape checks, timezone-aware timestamp parsing, future/expired/invalid lifetime and maximum-TTL checks. Duplicate/replay rejection now requires one atomic paired claim operation.
- `src/dispatcher/replay_store.py`: durable SQLite replay store using the repository's existing `Database` transaction manager. It creates a namespaced primary-key table, expires stale rows, and atomically claims request ID + nonce. If either value collides, a deliberate rollback prevents partial consumption. Storage errors propagate (fail closed).
- `tests/test_dispatcher_request_guard.py`: 11 deterministic unittest cases cover valid and malformed requests, timestamp and TTL rules, duplicate/replay rejection, fail-closed store errors, durable duplicate detection, rollback of partial claims, and expiry cleanup.
- `.github/workflows/ci.yml`: added `phase20/**` to the push-trigger branch filter so this implementation branch receives the repository's actual CI suite.

## Storage and deployment constraints

- SQLite is already a supported application backend. The replay store must use the same durable database file as the dispatcher and that file must be on persistent storage shared by every worker that can receive the same requests.
- Do not use SQLite `:memory:`, ephemeral runner storage, or separate per-worker database files for production replay protection.
- The current implementation is a storage adapter and validation boundary; the repository does not yet contain a dispatcher handler lookup/runtime entrypoint that wires it together with U20-3-05 authentication and commit verification. Runtime enforcement is not claimed.

## CI evidence

- CI workflow run: https://github.com/glad4u7-crypto/project-continue/actions/runs/46098486057
- Trigger commit: `55390631e49837764ee1f76e01a819d4e856d2db`
- At report update time, the GitHub Actions job had started and dependency installation was still in progress. No test result is claimed yet.
- Earlier implementation and test commits were read back from the target branch. Final read-back of all updated files and completed CI status is still required before PASS.

## Remaining acceptance gates

1. CI must complete successfully, including compile, focused test categories, complete pytest suite, container build and smoke test.
2. If CI fails, inspect the failing job logs, fix the cause, and rerun CI.
3. Add the runtime entrypoint integration with authenticated actor/repository/commit authorization before claiming end-to-end enforcement.
4. Read back the final implementation, tests, workflow and report from the branch and record their SHAs.

No merge to main and no live service/data modification.
