# U20-3-06 — Request replay protection and secure dispatcher validation boundary

- Repository: `glad4u7-crypto/project-continue`
- Branch: `phase20/secure-dispatcher-u20-3-01`
- Date: 2026-11-28 (Asia/Kolkata)
- Status: PASS — corrected full CI and final repository read-back verified

## Implemented artifacts

1. `schemas/dispatcher/request-envelope.v1.schema.json`
   - Canonical v1.0 envelope now agrees with the runtime shape: request UUID, nonce UUID, idempotency key, actor, repository numeric ID/name/commit SHA, nested task ID/arguments, issue/expiry times, optional trace ID.
2. `src/dispatcher/request_guard.py`
   - Strict envelope validation, actor/repository/task shape, commit SHA, idempotency-key format, timezone-aware timestamps, future/expired/TTL checks, and fail-closed atomic request-ID + nonce claims.
3. `src/dispatcher/replay_store.py`
   - SQLite replay claims through the repository's existing transaction manager. Atomic paired claims, duplicate rollback, expiry cleanup, and fail-closed storage errors.
4. `src/dispatcher/runtime.py`
   - `SecureDispatcher` orchestrates trusted authenticated-identity lookup, actor claim comparison, exact repository allow-list + live metadata check, minimum permission check, commit membership verifier, fixed task registry, closed task-argument validation, replay claim, then fixed handler lookup/invocation. Request-supplied actor fields are never authentication.
5. Tests (23 test methods total):
   - `tests/test_dispatcher_request_guard.py`: canonical envelope, malformed/expired/future requests, replay store durability, rollback, and storage failure tests.
   - `tests/test_dispatcher_runtime.py`: allow-listed dispatch, numeric/string GitHub ID normalization, actor spoof rejection, repository mismatch, insufficient permission, invalid commit, unknown task, unsafe arguments, replay rejection, and identity lookup failure.

## Runtime adapter boundary and explicit limitations

- The dispatcher requires host-supplied trusted adapters for authenticated GitHub identity, live repository metadata, permission lookup, and commit-SHA membership verification. It never treats envelope claims as proof.
- The connected ChatGPT GitHub connector's identity and repository permission evidence are recorded in U20-3-05. The current repository/application does not expose a credential-safe in-process adapter that can reuse ChatGPT's connected GitHub credential. No token/secret was read or copied into the app, and no pretend adapter was added.
- Therefore the authorization orchestration and handler ordering are implemented and testable, but live production credential adapter wiring is not claimed. It must be supplied through an approved host integration before deployment.
- SQLite replay protection requires a persistent database path shared by every worker. Do not use `:memory:`, ephemeral storage, or per-worker files in production. PostgreSQL backend support would need a matching replay-store adapter before selecting PostgreSQL for this dispatcher.

## CI evidence

- Corrected final CI run: https://github.com/glad4u7-crypto/project-continue/actions/runs/46105212163 — SUCCESS; all workflow steps passed. Full suite: 333 passed, 11 skipped, 10 subtests passed; coverage 79%; focused unit/integration/API/database categories also passed. PostgreSQL integration tests were skipped because opt-in DSNs were not configured.

- Earlier 11-test version full CI: https://github.com/glad4u7-crypto/project-continue/actions/runs/46098486057 — SUCCESS.
- Finalized 13-test guard-only version full CI: https://github.com/glad4u7-crypto/project-continue/actions/runs/46098670631 — SUCCESS.
- First canonical-envelope migration run: https://github.com/glad4u7-crypto/project-continue/actions/runs/46105007656 — FAILED because an older replay-store integration test still used the superseded flat envelope (4 failures; 319 passed; 11 skipped). Failure logs were inspected and the stale test was rewritten to the canonical v1.0 envelope.
- Runtime-integrated CI run 46105092157: FAILED one test (332 passed, 11 skipped). The failing test correctly exposed that the runtime treated a non-GitHub permission label `read` as equivalent to the policy's required `pull`. The permission map was tightened to accept only GitHub repository permission levels (`pull`, `triage`, `write`, `maintain`, `admin`) at or above the policy minimum.
- This run includes the corrected permission rule, all dispatcher tests, full compile, production container, compose validation, smoke test, focused test categories, and full suite.

## Acceptance

- Corrected CI run 46105212163 completed successfully; job `140856312496` confirms all workflow steps green.
- Final source, schema, test and report files were fetched from this branch after the CI run; no missing-file or read-back error occurred.
- No merge to main, no production credentials, and no live service/data modification.
