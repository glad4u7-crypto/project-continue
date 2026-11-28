# U20-3-06 — Malformed, expired, duplicate and replayed request rejection

- Repository: `glad4u7-crypto/project-continue`
- Branch: `phase20/secure-dispatcher-u20-3-01`
- Date: 2026-11-28 (Asia/Kolkata)
- Disposition: IMPLEMENTED — VERIFICATION PENDING; NOT PASS

## Changes committed

- `src/dispatcher/request_guard.py`: strict envelope shape, UUID request ID and nonce, actor/repository/commit/task shape checks, timezone-aware timestamp parsing, expiry and maximum-TTL checks, and fail-closed duplicate/replay claims.
- `tests/test_dispatcher_request_guard.py`: 9 deterministic unittest cases covering valid request, malformed fields/timestamp, expiry, excessive TTL, duplicate request ID, replayed nonce, malformed identity/repository/commit/task, and replay-store failure.
- GitHub commit for implementation: `9d2675251d9b2b873c0ff3b9f4f5970e30f90644`
- GitHub commit for tests: `ebb99d6c13969be2aa063eba74d734da3d500ee9`
- Both files were fetched back from the target branch and their expected content was confirmed.

## Security properties

- Unknown/missing envelope fields are rejected.
- Timestamps must be timezone-aware; expired, future-issued, non-positive-lifetime, and over-maximum-TTL requests are rejected.
- Request IDs and nonces must be UUIDs.
- Actor, repository, commit SHA, and task fields receive strict shape/allow-list checks.
- Duplicate request IDs and replayed nonces are rejected through an injected `claim_once` callback.
- Replay-store exceptions propagate; there is no permissive fallback.
- Replay claims must be backed by durable shared storage and atomic insert-if-absent. An in-memory set is explicitly insufficient.

## Verification gaps — do not mark PASS

- The GitHub connector can commit and read files but cannot run this repository's Python test suite in the current session.
- The durable atomic replay-store adapter is not implemented.
- Dispatcher runtime wiring and authenticated actor/repository/commit authorization integration are not implemented.
- Therefore the 9 tests are authored but NOT EXECUTED, and this unit is NOT PASS. Runtime replay protection is NOT claimed.

## Next actions

1. Run `python -m unittest tests.test_dispatcher_request_guard` (or the repository's configured test command) in CI and fix any import/style/integration failures.
2. Implement a durable shared atomic replay store with TTL cleanup and concurrency tests.
3. Wire request validation before handler lookup and combine it with U20-3-05 authenticated identity/repository/commit checks.
4. Re-run tests and read back the CI evidence before changing this unit to PASS.
