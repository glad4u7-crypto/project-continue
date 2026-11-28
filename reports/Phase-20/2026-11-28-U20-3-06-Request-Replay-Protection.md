# U20-3-06 — Request replay protection and secure dispatcher validation boundary

- Repository: `glad4u7-crypto/project-continue`
- Branch: `phase20/secure-dispatcher-u20-3-01`
- Date: 2026-11-28 (Asia/Kolkata)
- Status: IMPLEMENTED — FINAL CI RUN PENDING; NOT PASS UNTIL GREEN

## Implemented artifacts

1. `schemas/dispatcher/request-envelope.v1.schema.json`
   - Canonical v1.0 envelope now agrees with the runtime shape: request UUID, nonce UUID, idempotency key, actor, repository numeric ID/name/commit SHA, nested task ID/arguments, issue/expiry times, optional trace ID.
2. `src/dispatcher/request_guard.py`
   - Strict envelope validation, actor/repository/task shape, commit SHA, idempotency-key format, timezone-aware timestamps, future/expired/TTL checks, and fail-closed atomic request-ID + nonce claims.
3. `src/dispatcher/replay_store.py`
   - SQLite replay claims through the repository's existing transaction manager. Atomic paired claims, duplicate rollback, expiry cleanup, and fail-closed storage errors.
4. `src/dispatcher/runtime.py`
   - `SecureDispatcher` orchestrates trusted authenticated-identity lookup, actor claim comparison, exact repository allow-list + live metadata check, minimum permission check, commit membership verifier, fixed task registry, closed task-argument validation, replay claim, then fixed handler lookup/invocation. Request-supplied actor fields are never authentication.
5. Tests:
   - `tests/test_dispatcher_request_guard.py`: canonical envelope, malformed/expired/future requests, replay store durability, rollback, and storage failure tests.
   - `tests/test_dispatcher_runtime.py`: allow-listed dispatch, numeric/string GitHub ID normalization, actor spoof rejection, repository mismatch, insufficient permission, invalid commit, unknown task, unsafe arguments, replay rejection, and identity lookup failure.

## Runtime adapter boundary and explicit limitations

- The dispatcher requires host-supplied trusted adapters for authenticated GitHub identity, live repository metadata, permission lookup, and commit-SHA membership verification. It never treats envelope claims as proof.
- The connected ChatGPT GitHub connector's identity and repository permission evidence are recorded in U20-3-05. The current repository/application does not expose a credential-safe in-process adapter that can reuse ChatGPT's connected GitHub credential. No token/secret was read or copied into the app, and no pretend adapter was added.
- Therefore the authorization orchestration and handler ordering are implemented and testable, but live production credential adapter wiring is not claimed. It must be supplied through an approved host integration before deployment.
- SQLite replay protection requires a persistent database path shared by every worker. Do not use `:memory:`, ephemeral storage, or per-worker files in production. PostgreSQL backend support would need a matching replay-store adapter before selecting PostgreSQL for this dispatcher.

## CI evidence

- Earlier 11-test version full CI: https://github.com/glad4u7-crypto/project-continue/actions/runs/46098486057 — SUCCESS.
- Finalized 13-test guard-only version full CI: https://github.com/glad4u7-crypto/project-continue/actions/runs/46098670631 — SUCCESS.
- First canonical-envelope migration run: https://github.com/glad4u7-crypto/project-continue/actions/runs/46105007656 — FAILED because an older replay-store integration test still used the superseded flat envelope (4 failures; 319 passed; 11 skipped). Failure logs were inspected and the stale test was rewritten to the canonical v1.0 envelope.
- Runtime-integrated CI run 46105092157: FAILED one test (332 passed, 11 skipped). The failing test correctly exposed that the runtime treated a non-GitHub permission label `read` as equivalent to the policy's required `pull`. The permission map was tightened to accept only GitHub repository permission levels (`pull`, `triage`, `write`, `maintain`, `admin`) at or above the policy minimum.
- Corrected final CI run: https://github.com/glad4u7-crypto/project-continue/actions/runs/46105212163 — queued/in progress at the time of this update. This run includes the corrected permission rule, all dispatcher tests, full compile, production container, compose validation, smoke test, focused test categories, and full suite.

## Acceptance

- Do not mark PASS until run 46105092157 is completed successfully and final files are read back from this branch.
- If the run fails, inspect its job logs, fix and rerun.
- No merge to main, no production credentials, and no live service/data modification.
